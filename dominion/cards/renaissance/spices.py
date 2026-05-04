"""Spices: Treasure ($5). $2. +1 Buy.

When you gain this, +2 Coffers.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Spices(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Spices",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.TREASURE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        player.coin_tokens += 2
