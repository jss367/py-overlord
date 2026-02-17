"""AI adapter that receives actions from an RL agent."""

import queue
from typing import Optional

from dominion.ai.base_ai import AI
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState


class _RLStrategy:
    """Stub strategy for compatibility with GameState logging."""
    name = "RL Agent"


class RLAI(AI):
    """AI that communicates with the RL environment via queues.

    When the game engine calls a choose_* method, RLAI puts the choices
    on the choice_queue and blocks until the env provides an action via
    the action_queue. This allows the game to run in a background thread
    while the env controls the RL agent's decisions.
    """

    def __init__(self, name: str = "RLAI"):
        self._name = name
        self.strategy = _RLStrategy()
        # Queues for env <-> game thread communication
        self.choice_queue: queue.Queue = queue.Queue()
        self.action_queue: queue.Queue = queue.Queue()

    @property
    def name(self) -> str:
        return self._name

    def _request_decision(self, decision_type: str, state: GameState,
                          choices: list) -> Optional[Card]:
        """Put choices on queue and wait for env to provide action."""
        self.choice_queue.put((decision_type, state, choices))
        return self.action_queue.get()

    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        return self._request_decision("action", state, choices)

    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        return self._request_decision("treasure", state, choices)

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        return self._request_decision("buy", state, choices)

    def choose_card_to_trash(self, state: GameState, choices: list[Card]) -> Optional[Card]:
        return self._request_decision("trash", state, choices)
