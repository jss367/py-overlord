from ..base_card import Card, CardCost, CardStats, CardType


class Trail(Card):
    def __init__(self):
        super().__init__(
            name="Trail",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION],
        )
