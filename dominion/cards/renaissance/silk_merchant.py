"""Silk Merchant: Action ($4). +2 Cards. +1 Buy.

When you gain or trash this, +1 Coffers and +1 Villager.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class SilkMerchant(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Silk Merchant",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2, buys=1),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        player.coin_tokens += 1
        player.villagers += 1

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        player.coin_tokens += 1
        player.villagers += 1
