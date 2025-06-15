from ..base_card import Card, CardCost, CardStats, CardType


class Inn(Card):
    def __init__(self):
        super().__init__(
            name="Inn",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, cards=2),
            types=[CardType.ACTION],
        )
