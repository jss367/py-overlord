from ..base_card import Card, CardCost, CardStats, CardType


class FirstMate(Card):
    def __init__(self):
        super().__init__(
            name="First Mate",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
