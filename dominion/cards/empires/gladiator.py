from ..base_card import Card, CardCost, CardStats, CardType


class Gladiator(Card):
    partner_card_name = "Fortune"

    def __init__(self):
        super().__init__(
            name="Gladiator",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION],
        )
