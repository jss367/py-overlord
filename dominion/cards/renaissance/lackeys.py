"""Lackeys: Action ($2). +2 Cards.

When you gain this, +2 Villagers.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Lackeys(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Lackeys",
            cost=CardCost(coins=2),
            stats=CardStats(cards=2),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        player.villagers += 2
