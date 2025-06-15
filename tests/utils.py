from dominion.ai.base_ai import AI
from typing import Optional
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState

class DummyAI(AI):
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
