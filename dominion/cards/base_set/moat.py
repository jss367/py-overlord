from typing import List
from ..base_card import Card, CardCost, CardStats, CardType


class Moat(Card):
    def __init__(self):
        super().__init__(
            name="Moat",
            cost=CardCost(coins=2),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION]
        )
