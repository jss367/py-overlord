"""Gymnasium environment for Dominion."""

import queue
import random
import threading
from typing import Any, Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.rl.action_encoder import ActionEncoder
from dominion.rl.random_ai import RandomAI
from dominion.rl.rl_ai import RLAI
from dominion.rl.state_encoder import StateEncoder


class DominionEnv(gym.Env):
    """Gymnasium environment for training RL agents on Dominion.

    The agent plays as player 0 against an opponent (default: RandomAI).
    The game runs in a background thread; each step() corresponds to one
    decision point (action, treasure, or buy choice).

    Observations are encoded game states. Actions are card choices.
    Reward is +1 for win, -1 for loss, 0 otherwise.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        kingdom_cards: list[str],
        opponent_ai: Optional[Any] = None,
        max_turns: int = 100,
    ):
        super().__init__()

        self.kingdom_cards = list(kingdom_cards)
        self._opponent_factory = opponent_ai  # AI instance or None
        self.max_turns = max_turns

        # Encoders
        self.state_encoder = StateEncoder(kingdom_cards)
        self.action_encoder = ActionEncoder(kingdom_cards)

        # Gym spaces
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.state_encoder.observation_size,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(self.action_encoder.action_size)

        # Game state (set during reset)
        self.game_state: Optional[GameState] = None
        self.rl_ai: Optional[RLAI] = None
        self._game_thread: Optional[threading.Thread] = None
        self._current_choices: list = []
        self._current_decision_type: str = ""
        self._game_done = False
        self._game_error: Optional[Exception] = None

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        # Clean up previous game thread
        if self._game_thread is not None and self._game_thread.is_alive():
            # Unblock the game thread so it can exit
            if self.rl_ai is not None:
                self.rl_ai.action_queue.put(None)
            self._game_thread.join(timeout=5)

        # Create fresh AIs
        self.rl_ai = RLAI(name="RLAgent")
        opponent = RandomAI() if self._opponent_factory is None else self._opponent_factory

        # Set up game
        self.game_state = GameState(players=[], supply={})
        # Suppress default logging
        self.game_state.log_callback = lambda msg: None
        kingdom_card_objects = [get_card(name) for name in self.kingdom_cards]
        self.game_state.initialize_game(
            [self.rl_ai, opponent],
            kingdom_card_objects,
        )

        self._game_done = False
        self._game_error = None

        # Start game in background thread
        self._game_thread = threading.Thread(target=self._run_game, daemon=True)
        self._game_thread.start()

        # Wait for first decision point
        self._wait_for_decision()

        obs = self._get_observation()
        info = self._get_info()
        return obs, info

    def _find_choice_card(self, action: int) -> Optional[Any]:
        """Find the actual card object from choices that matches the action index.

        The game engine uses object identity for hand.remove(), so we must
        return the exact card instance from the choices list, not a new one.
        """
        if action == self.action_encoder.pass_action_index:
            return None
        target_name = self.action_encoder.all_cards[action]
        for choice in self._current_choices:
            if choice is not None and choice.name == target_name:
                return choice
        return None

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        if self._game_done:
            # Game already over
            obs = self._get_observation()
            return obs, 0.0, True, False, self._get_info()

        # Validate action against mask
        mask = self.action_encoder.get_action_mask(self._current_choices)
        if not mask[action]:
            # Invalid action - pick first valid one
            valid_actions = np.where(mask)[0]
            action = valid_actions[0]

        # Find the actual card object from the choices list (not a new instance)
        card = self._find_choice_card(action)

        # Send action to game thread
        self.rl_ai.action_queue.put(card)

        # Wait for next decision point or game end
        self._wait_for_decision()

        # Check termination
        terminated = self._game_done
        truncated = not terminated and self.game_state.turn_number > self.max_turns

        # Calculate reward
        reward = 0.0
        if terminated or truncated:
            reward = self._calculate_reward()

        obs = self._get_observation()
        info = self._get_info()
        return obs, reward, terminated, truncated, info

    def _run_game(self) -> None:
        """Run the game loop in a background thread."""
        try:
            while not self.game_state.is_game_over():
                if self.game_state.turn_number > self.max_turns:
                    break
                self.game_state.play_turn()
        except Exception as e:
            self._game_error = e
        finally:
            # Signal that the game is done
            self.rl_ai.choice_queue.put(("done", None, None))

    def _wait_for_decision(self) -> None:
        """Block until the RL agent needs to make a decision or game ends."""
        try:
            decision_type, state, choices = self.rl_ai.choice_queue.get(timeout=30)
        except queue.Empty:
            self._game_done = True
            return

        if decision_type == "done":
            self._game_done = True
            return

        self._current_decision_type = decision_type
        self._current_choices = choices

    def _get_observation(self) -> np.ndarray:
        return self.state_encoder.encode(self.game_state, player_index=0)

    def _get_info(self) -> dict:
        if self._game_done:
            # Return all-valid mask when game is over
            mask = np.ones(self.action_encoder.action_size, dtype=bool)
        else:
            mask = self.action_encoder.get_action_mask(self._current_choices)
        return {"action_mask": mask}

    def _calculate_reward(self) -> float:
        rl_player = self.game_state.players[0]
        opponent = self.game_state.players[1]
        rl_vp = rl_player.get_victory_points()
        opp_vp = opponent.get_victory_points()
        if rl_vp > opp_vp:
            return 1.0
        elif rl_vp < opp_vp:
            return -1.0
        return 0.0

    def close(self) -> None:
        if self._game_thread is not None and self._game_thread.is_alive():
            if self.rl_ai is not None:
                self.rl_ai.action_queue.put(None)
            self._game_thread.join(timeout=5)
