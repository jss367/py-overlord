from ..base_card import Card, CardCost, CardStats, CardType


class Scheme(Card):
    def __init__(self):
        super().__init__(
            name="Scheme",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )
