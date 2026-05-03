from ..base_card import Card, CardCost, CardStats, CardType


class Fishmonger(Card):
    """Action-Shadow ($2): +1 Buy, +$1."""

    def __init__(self):
        super().__init__(
            name="Fishmonger",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.ACTION, CardType.SHADOW],
        )
