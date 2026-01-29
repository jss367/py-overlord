"""AI adapter that receives actions from an RL agent."""

from typing import Optional

from dominion.ai.base_ai import AI
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState


class _RLStrategy:
    """Stub strategy for compatibility with GameState logging."""
    name = "RL Agent"


class RLAI(AI):
    """AI that returns pre-set actions from an RL agent.

    This adapter allows the RL environment to control game decisions.
    Before each decision point, the environment sets the action via
    set_next_action(), then the game engine calls the appropriate
    choose_* method which returns that action.
    """

    def __init__(self, name: str = "RLAI"):
        self._name = name
        self._pending_action: Optional[Card] = None
        self.strategy = _RLStrategy()

    @property
    def name(self) -> str:
        return self._name

    def set_next_action(self, action: Optional[Card]) -> None:
        """Queue the next action to be returned by choose_* methods."""
        self._pending_action = action

    def _get_and_clear_action(self) -> Optional[Card]:
        """Return pending action and clear it."""
        action = self._pending_action
        self._pending_action = None
        return action

    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Return the queued action card."""
        return self._get_and_clear_action()

    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Return the queued treasure card."""
        return self._get_and_clear_action()

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Return the queued buy choice."""
        return self._get_and_clear_action()

    def choose_card_to_trash(self, state: GameState, choices: list[Card]) -> Optional[Card]:
        """Return the queued card to trash."""
        return self._get_and_clear_action()
