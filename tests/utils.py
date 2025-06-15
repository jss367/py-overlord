from dominion.ai.base_ai import AI
from typing import Optional
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState

class DummyAI(AI):
    def __init__(self):
        self.strategy = None

    @property
    def name(self) -> str:
        return "DummyAI-1"

    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        return None

    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        return None

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        return None

    def choose_card_to_trash(self, state: GameState, choices: list[Card]) -> Optional[Card]:
        return None


class BuyEventAI(DummyAI):
    """AI that buys an event or project if available."""

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]):
        for choice in choices:
            if getattr(choice, "is_event", False) or getattr(choice, "is_project", False):
                return choice
        return None


class TrashFirstAI(BuyEventAI):
    """AI that always trashes the first available card."""

    def choose_card_to_trash(self, state: GameState, choices: list[Card]) -> Optional[Card]:
        return choices[0] if choices else None


class ChooseFirstActionAI(BuyEventAI):
    """AI that always plays the first available action."""

    def choose_action(self, state: GameState, choices: list[Optional[Card]]):
        for ch in choices:
            if ch is not None:
                return ch
        return None
