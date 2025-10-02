from ..base_card import Card, CardCost, CardStats, CardType


class WalledVillage(Card):
    def __init__(self):
        super().__init__(
            name="Walled Village",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )
