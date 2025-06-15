from ..base_card import Card, CardCost, CardStats, CardType


class Trader(Card):
    def __init__(self):
        super().__init__(
            name="Trader",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION],
        )
