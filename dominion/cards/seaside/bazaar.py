"""Implementation of the Bazaar card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Bazaar(Card):
    def __init__(self):
        super().__init__(
            name="Bazaar",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=2, coins=1),
            types=[CardType.ACTION],
        )
