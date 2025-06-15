from ..base_card import Card, CardCost, CardStats, CardType


class Patrol(Card):
    def __init__(self):
        super().__init__(
            name="Patrol",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=3),
            types=[CardType.ACTION],
        )
