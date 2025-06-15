from ..base_card import Card, CardCost, CardStats, CardType


class WorkersVillage(Card):
    def __init__(self):
        super().__init__(
            name="Workers' Village",
            cost=CardCost(coins=4),
            stats=CardStats(actions=2, cards=1, buys=1),
            types=[CardType.ACTION],
        )
