from ..base_card import Card, CardCost, CardStats, CardType


class Laboratory(Card):
    def __init__(self):
        super().__init__(
            name="Laboratory",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=2),
            types=[CardType.ACTION],
        )
