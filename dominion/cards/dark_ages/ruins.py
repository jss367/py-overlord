"""Implementation of the Ruins pile and its five distinct cards."""

from __future__ import annotations

import random
from ..base_card import Card, CardCost, CardStats, CardType


class _BaseRuinsCard(Card):
    def __init__(self, name: str, stats: CardStats):
        super().__init__(
            name=name,
            cost=CardCost(coins=0),
            stats=stats,
            types=[CardType.ACTION],
        )


class AbandonedMine(_BaseRuinsCard):
    def __init__(self):
        super().__init__("Abandoned Mine", CardStats(coins=1))


class RuinedMarket(_BaseRuinsCard):
    def __init__(self):
        super().__init__("Ruined Market", CardStats(buys=1))


class RuinedVillage(_BaseRuinsCard):
    def __init__(self):
        super().__init__("Ruined Village", CardStats(actions=1))


class RuinedLibrary(_BaseRuinsCard):
    def __init__(self):
        super().__init__("Ruined Library", CardStats(cards=1))

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        discard_choice = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 1
        )
        if discard_choice:
            card = discard_choice[0]
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)


class Survivors(_BaseRuinsCard):
    def __init__(self):
        super().__init__("Survivors", CardStats())

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list[Card] = []

        for _ in range(2):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        discard_all = player.ai.should_discard_with_survivors(
            game_state, player, list(revealed)
        )

        if discard_all:
            for card in revealed:
                game_state.discard_card(player, card)
            return

        ordered = player.ai.order_cards_for_survivors(
            game_state, player, list(revealed)
        )
        if not ordered or sorted(ordered, key=id) != sorted(revealed, key=id):
            ordered = player.ai.order_cards_for_patrol(game_state, player, revealed)

        for card in reversed(ordered):
            player.deck.append(card)


class Ruins(Card):
    VARIANT_CLASSES: tuple[type[Card], ...] = (
        AbandonedMine,
        RuinedMarket,
        RuinedLibrary,
        RuinedVillage,
        Survivors,
    )

    def __init__(self):
        super().__init__(
            name="Ruins",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def may_be_bought(self, game_state) -> bool:  # pragma: no cover - not in supply
        return False

    def starting_supply(self, game_state) -> int:
        if getattr(game_state, "ruins_pile", None):
            return len(game_state.ruins_pile)

        player_count = len(game_state.players)
        total = 10 if player_count <= 2 else 20 if player_count == 3 else 30
        copies_each = total // len(self.VARIANT_CLASSES)

        pile: list[Card] = []
        for variant in self.VARIANT_CLASSES:
            for _ in range(copies_each):
                pile.append(variant())

        random.shuffle(pile)
        game_state.ruins_pile = pile
        return len(game_state.ruins_pile)

    def on_gain(self, game_state, player):
        if not getattr(game_state, "ruins_pile", None):
            return

        actual = game_state.ruins_pile.pop() if game_state.ruins_pile else None
        if not actual:
            return

        original_name = getattr(actual, "variant_name", actual.name)
        actual.variant_name = original_name
        actual.name = "Ruins"

        self._replace_placeholder(player, actual)
        actual.on_gain(game_state, player)

    def _replace_placeholder(self, player, actual: Card) -> None:
        for zone in (player.discard, player.deck, player.hand, player.in_play):
            if self in zone:
                idx = zone.index(self)
                zone[idx] = actual
                return

        # Fallback: if somehow not found, add to discard
        player.discard.append(actual)


__all__ = [
    "Ruins",
    "AbandonedMine",
    "RuinedMarket",
    "RuinedVillage",
    "RuinedLibrary",
    "Survivors",
]
