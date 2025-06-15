from ..base_card import Card, CardCost, CardStats, CardType


class Torturer(Card):
    def __init__(self):
        super().__init__(
            name="Torturer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )
