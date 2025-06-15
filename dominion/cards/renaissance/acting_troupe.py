from ..base_card import Card, CardCost, CardStats, CardType


class ActingTroupe(Card):
    def __init__(self):
        super().__init__(
            name="Acting Troupe",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )
