"""Implementation of the Woodcutter (1E) card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Woodcutter(Card):
    """Action ($3): +1 Buy, +$2."""

    def __init__(self):
        super().__init__(
            name="Woodcutter",
            cost=CardCost(coins=3),
            stats=CardStats(buys=1, coins=2),
            types=[CardType.ACTION],
        )
