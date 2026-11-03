from ..base_card import Card, CardCost, CardStats, CardType


class NomadCamp(Card):
    default_gain_destination = "deck"

    def __init__(self):
        super().__init__(
            name="Nomad Camp",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION],
        )
