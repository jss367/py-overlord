"""Decision-level Gymnasium environment backed by the Dominion rules engine."""

import queue
import random
import threading
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from dominion.cards.registry import get_card
from dominion.game.game_state import GAME_TURN_LIMIT, GameState
from dominion.rl.action_encoder import ActionEncoder
from dominion.rl.random_ai import RandomAI
from dominion.rl.rl_ai import GameCancelled, RLAI
from dominion.rl.state_encoder import StateEncoder


class _TrainingGameState(GameState):
    """Let the environment enforce its cap at a real policy decision."""

    def is_game_over(self) -> bool:
        return super().is_game_over(ignore_turn_limit=True)


class DominionEnv(gym.Env):
    """One active game per process (the rules engine uses Python's global RNG).

    ``kingdoms`` varies the board each episode while ``vocabulary`` keeps action
    indices fixed. A callable opponent receives the current kingdom and must
    return a fresh AI. Existing single-board callers retain their old interface.
    Time limits stop at the next policy decision and award zero. Natural game
    endings before that decision retain their ordinary terminal reward.
    """

    metadata = {"render_modes": []}

    def __init__(self, kingdom_cards: list[str], opponent_ai: Any = None,
                 max_turns: int = 100, *, kingdoms=None, vocabulary=None,
                 state_encoder=None, randomize_seats: bool = False):
        super().__init__()
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.kingdom_cards = list(kingdom_cards)
        self.kingdoms = [list(k) for k in (kingdoms or [kingdom_cards])]
        self._opponent_factory = opponent_ai
        self.max_turns = max_turns
        self.randomize_seats = randomize_seats
        self.player_index = 0
        vocabulary = list(vocabulary or kingdom_cards)
        if any(not set(k) <= set(vocabulary) for k in self.kingdoms):
            raise ValueError("Every kingdom must fit the action vocabulary")
        self.state_encoder = state_encoder or StateEncoder(vocabulary)
        self.action_encoder = ActionEncoder(vocabulary)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(self.state_encoder.observation_size,), dtype=np.float32)
        self.action_space = spaces.Discrete(self.action_encoder.action_size)
        self.game_state = None
        self.rl_ai = None
        self._game_thread = None
        self._current_choices = []
        self._current_decision_type = ""
        self._game_done = False
        self._truncated = False
        self._truncate_at_next_decision = False
        self._game_error = None

    def reset(self, *, seed=None, options=None):
        self.close()
        super().reset(seed=seed)
        options = options or {}
        kingdom = options.get("kingdom")
        if kingdom is not None and list(kingdom) not in self.kingdoms:
            raise ValueError("Requested kingdom is not in this environment's split")
        self.kingdom_cards = list(kingdom if kingdom is not None else
                                  self.kingdoms[int(self.np_random.integers(len(self.kingdoms)))])
        self.player_index = int(options.get("seat", self.np_random.integers(2)
                                           if self.randomize_seats else 0))
        if self.player_index not in (0, 1):
            raise ValueError("seat must be 0 or 1")
        game_seed = int(seed if seed is not None else self.np_random.integers(2**32))
        random.seed(game_seed)
        self.rl_ai = RLAI(name="RLAgent")
        opponent = self._opponent_factory
        if opponent is None:
            opponent = RandomAI()
        elif callable(opponent):
            opponent = opponent(self.kingdom_cards)
        ais = [self.rl_ai, opponent] if self.player_index == 0 else [opponent, self.rl_ai]
        self.game_state = _TrainingGameState(players=[], supply={})
        self.game_state.log_callback = lambda msg: None
        self.game_state.initialize_game(ais, [get_card(n) for n in self.kingdom_cards])
        self._game_done = self._truncated = False
        self._truncate_at_next_decision = False
        self._game_error = None
        self._game_thread = threading.Thread(target=self._run_game, daemon=True)
        self._game_thread.start()
        self._wait_for_decision()
        return self._get_observation(), self._get_info()

    def _find_choice_card(self, action):
        if action == self.action_encoder.pass_action_index:
            return None
        name = self.action_encoder.all_cards[action]
        return next(c for c in self._current_choices if c is not None and c.name == name)

    def step(self, action):
        if self.game_state is None or self._game_thread is None:
            raise RuntimeError("Call reset before step")
        if self._game_done:
            return self._get_observation(), 0.0, not self._truncated, self._truncated, self._get_info()
        mask = self.action_encoder.get_action_mask(self._current_choices)
        if not isinstance(action, (int, np.integer)) or not 0 <= action < len(mask) or not mask[action]:
            raise ValueError(f"Illegal action index: {action}")
        self.rl_ai.action_queue.put(self._find_choice_card(action))
        self._wait_for_decision()
        reward = self._calculate_reward() if self._game_done and not self._truncated else 0.0
        return (self._get_observation(), reward, self._game_done and not self._truncated,
                self._truncated, self._get_info())

    def _run_game(self):
        try:
            while True:
                terminated, capped = episode_status(self.game_state, self.max_turns)
                if terminated:
                    break
                # Finish the transition to the next decision, including the
                # opponent turn when needed. The value function is trained
                # on decision observations, not arbitrary turn boundaries.
                self._truncate_at_next_decision |= capped
                if self.rl_ai.cancelled:
                    break
                self.game_state.play_turn()
        except GameCancelled:
            pass
        except Exception as exc:
            self._game_error = exc
        finally:
            self.rl_ai.choice_queue.put(("done", None, None))

    def _wait_for_decision(self):
        try:
            decision_type, _, choices = self.rl_ai.choice_queue.get(timeout=30)
        except queue.Empty as exc:
            self.close()
            raise TimeoutError("Game engine did not produce a decision") from exc
        if decision_type == "done":
            self._game_done = True
            self._current_choices = []
            self._current_decision_type = ""
            if self._game_error is not None:
                raise RuntimeError("Dominion game engine failed") from self._game_error
        else:
            self._current_decision_type = decision_type
            self._current_choices = choices
            if self._truncate_at_next_decision:
                self._game_done = self._truncated = True

    def _get_observation(self):
        encode_decision = getattr(self.state_encoder, "encode_decision", None)
        if encode_decision:
            return encode_decision(self.game_state, self.player_index, self._current_decision_type)
        return self.state_encoder.encode(self.game_state, self.player_index)

    def _get_info(self):
        mask = self.action_encoder.get_action_mask(self._current_choices)
        if self._game_done and not self._current_choices:
            mask[self.action_encoder.pass_action_index] = True
        return {"action_mask": mask, "decision_type": self._current_decision_type,
                "seat": self.player_index, "kingdom": list(self.kingdom_cards)}

    def _calculate_reward(self):
        return game_reward(self.game_state, self.player_index)

    def close(self):
        if self._game_thread is not None:
            if self._game_thread.is_alive():
                self.rl_ai.cancel()
            self._game_thread.join(timeout=5)
            if self._game_thread.is_alive():
                raise RuntimeError("Game thread failed to stop; refusing to start another game")
            self._game_thread = None


def game_reward(state, player_index):
    """Official two-player result, including fewer-turns tiebreak."""
    scores = [(p.get_victory_points(), -p.turns_taken) for p in state.players]
    ours, theirs = scores[player_index], scores[1 - player_index]
    return float((ours > theirs) - (ours < theirs))


def episode_status(state, max_turns):
    """Separate rule endings from both harness and engine safety caps.

    A genuine game ending takes precedence when the final cleanup also
    advances past the turn limit. Fleet must finish its extra round before
    a depleted pile is treated as a completed game.
    """
    ended = state.is_game_over()
    natural_end = ended and (state._normal_game_end_reached() or state.fleet_extra_round_active)
    if natural_end:
        return True, False
    capped = state.phase == "start" and state.turn_number > min(max_turns, GAME_TURN_LIMIT)
    return ended and not capped, capped
