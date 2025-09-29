from ..base_card import Card, CardCost, CardStats, CardType


class Haggler(Card):
    def __init__(self):
        super().__init__(
            name="Haggler",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )
