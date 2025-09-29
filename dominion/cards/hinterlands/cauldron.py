from ..base_card import Card, CardCost, CardStats, CardType


class Cauldron(Card):
    def __init__(self):
        super().__init__(
            name="Cauldron",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.TREASURE, CardType.ATTACK],
        )
