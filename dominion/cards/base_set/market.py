from ..base_card import Card, CardCost, CardStats, CardType


class Market(Card):
    def __init__(self):
        super().__init__(
            name="Market",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1, coins=1, buys=1),
            types=[CardType.ACTION],
        )
