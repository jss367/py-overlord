from abc import ABC, abstractmethod
from typing import Optional

from dominion.cards.base_card import Card
from dominion.game.game_state import GameState


class AI(ABC):
    """Base class for all AIs."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose an action to play from available choices."""
        pass

    @abstractmethod
    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose a treasure to play from available choices."""
        pass

    @abstractmethod
    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose a card to buy from available choices."""
        pass

    @abstractmethod
    def choose_card_to_trash(self, state: GameState, choices: list[Card]) -> Optional[Card]:
        """Choose a card to trash from available choices."""
        pass

    def choose_way(self, state: GameState, card: Card, ways: list) -> Optional[object]:
        """Choose a Way to use when playing a card. Default is none."""
        return None

    def use_amphora_now(self, state: GameState) -> bool:
        """Decide whether to take Amphora's bonus immediately."""
        return True
