from abc import ABC, abstractmethod
from typing import Optional

from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


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

    def choose_cards_to_trash(self, state: GameState, choices: list[Card], count: int) -> list[Card]:
        """Select up to ``count`` cards to trash, defaulting to single picks."""

        remaining = list(choices)
        selected: list[Card] = []

        while remaining and len(selected) < count:
            choice = self.choose_card_to_trash(state, remaining)
            if choice is None or choice not in remaining:
                break
            selected.append(choice)
            remaining.remove(choice)

        return selected

    def choose_cards_to_discard(
        self,
        state: GameState,
        player: PlayerState,
        choices: list[Card],
        count: int,
        *,
        reason: Optional[str] = None,
    ) -> list[Card]:
        """Choose up to ``count`` cards to discard from ``choices``.

        Default heuristic prefers to discard obviously low-value cards:
        Curses, low-cost non-action Victory, then Copper, then by cost.

        ``reason`` can be used by subclasses to tailor decisions (e.g. "torturer").
        """

        def discard_priority(card: Card) -> tuple[int, int, str]:
            if card.name == "Curse":
                return (0, 0, card.name)
            # Non-action green cards are typically dead in hand; prefer cheaper ones first
            if card.is_victory and not card.is_action and card.cost.coins <= 2:
                return (1, card.cost.coins, card.name)
            if card.name == "Copper":
                return (2, 0, card.name)
            # Otherwise rank by coin cost (cheaper first)
            return (3, card.cost.coins, card.name)

        available = list(choices)
        ordered = sorted(available, key=discard_priority)
        return ordered[: max(0, min(count, len(ordered)))]

    def should_reveal_trader(self, state: GameState, player: PlayerState, gained_card: Card, *, to_deck: bool) -> bool:
        """Decide whether to reveal Trader to exchange a gain for Silver."""

        return False

    def choose_way(self, state: GameState, card: Card, ways: list) -> Optional[object]:
        """Choose a Way to use when playing a card. Default is none."""
        return None

    def use_amphora_now(self, state: GameState) -> bool:
        """Decide whether to take Amphora's bonus immediately."""
        return True

    def choose_torturer_attack(self, state: GameState, player: PlayerState) -> bool:
        """Choose whether to discard two cards or gain a Curse from Torturer.

        The default heuristic discards when at least two low-value cards are
        present (Curses, Estates, or Coppers). Otherwise, it keeps the valuable
        hand and accepts the Curse.
        """

        hand = list(player.hand)

        if len(hand) < 2:
            return False

        def is_low_value(card: Card) -> bool:
            if card.name == "Curse":
                return True
            if card.name == "Copper":
                return True
            if card.is_victory and not card.is_action and card.cost.coins <= 2:
                return True
            return False

        low_value_cards = [card for card in hand if is_low_value(card)]
        return len(low_value_cards) >= 2

    def order_cards_for_patrol(self, state: GameState, player: PlayerState, cards: list[Card]) -> list[Card]:
        """Return cards in draw priority order for Patrol's topdeck effect."""

        def priority(card: Card) -> tuple[int, int, str]:
            score = 0
            if card.is_action:
                score += 200
            if card.is_treasure:
                score += 100 + card.cost.coins
            score += card.cost.coins
            return (score, card.stats.cards, card.name)

        return sorted(cards, key=priority, reverse=True)
