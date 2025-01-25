from typing import List
from ..base_card import Card, CardCost, CardStats, CardType

class Village(Card):
    def __init__(self):
        super().__init__(
            name="Village",
            cost=CardCost(coins=3),
            stats=CardStats(actions=2, cards=1),
            types=[CardType.ACTION]
        )
