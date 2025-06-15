from ..base_card import Card, CardCost, CardStats, CardType


class Taskmaster(Card):
    def __init__(self):
        super().__init__(
            name="Taskmaster",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )
