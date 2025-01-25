from typing import List
from ..base_card import Card, CardCost, CardStats, CardType


class Smithy(Card):
    def __init__(self):
        super().__init__(
            name="Smithy",
            cost=CardCost(coins=4),
            stats=CardStats(cards=3),
            types=[CardType.ACTION]
        )
