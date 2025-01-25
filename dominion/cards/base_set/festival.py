from typing import List
from ..base_card import Card, CardCost, CardStats, CardType


class Festival(Card):
    def __init__(self):
        super().__init__(
            name="Festival",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, coins=2, buys=1),
            types=[CardType.ACTION]
        )
