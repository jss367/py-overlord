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

    def choose_count_first_option(
        self, state: GameState, player: PlayerState, choices: list[str]
    ) -> str:
        junk = {"Curse", "Estate", "Hovel", "Copper"}
        if "discard" in choices and len(player.hand) >= 2:
            junk_in_hand = sum(1 for card in player.hand if card.name in junk)
            if junk_in_hand >= 2 or len(player.hand) <= 2:
                return "discard"
        if "topdeck" in choices and player.hand:
            return "topdeck"
        if "gain_copper" in choices:
            return "gain_copper"
        return choices[0]

    def choose_count_second_option(
        self, state: GameState, player: PlayerState, choices: list[str]
    ) -> str:
        if "trash_hand" in choices and player.hand:
            junk = {"Curse", "Estate", "Hovel", "Copper"}
            if all(card.name in junk for card in player.hand):
                return "trash_hand"
        if "gain_duchy" in choices and state.supply.get("Duchy", 0) > 0:
            if state.supply.get("Province", 0) <= 4:
                return "gain_duchy"
        if "coins" in choices:
            return "coins"
        return choices[0]

    def choose_card_to_topdeck(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        if not choices:
            return None

        return max(choices, key=lambda c: (c.cost.coins, c.stats.cards, c.name))

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

    def should_discard_ironmonger_reveal(
        self, state: GameState, player: PlayerState, revealed: Card
    ) -> bool:
        if revealed.name == "Curse":
            return True
        if revealed.is_victory and not revealed.is_action:
            return True
        if revealed.name in {"Ruins", "Hovel"}:
            return True
        return False

    def should_react_with_beggar(self, state: GameState, player: PlayerState) -> bool:
        return state.supply.get("Silver", 0) >= 1

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

    def choose_rebuild_name(
        self, state: GameState, player: PlayerState, options: list[str]
    ) -> str:
        for preferred in ("Province", "Duchy", "Estate"):
            if preferred in options:
                return preferred
        return options[0] if options else "Province"

    def should_discard_with_survivors(
        self, state: GameState, player: PlayerState, cards: list[Card]
    ) -> bool:
        def is_junk(card: Card) -> bool:
            if card.name == "Curse":
                return True
            if card.is_victory and not card.is_action and card.cost.coins <= 2:
                return True
            return False

        return all(is_junk(card) for card in cards)

    def order_cards_for_survivors(
        self, state: GameState, player: PlayerState, cards: list[Card]
    ) -> list[Card]:
        return self.order_cards_for_patrol(state, player, cards)

    def should_trash_hovel(
        self, state: GameState, player: PlayerState, gained_card: Card
    ) -> bool:
        return True
