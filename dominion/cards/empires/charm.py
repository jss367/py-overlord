from ..base_card import Card, CardCost, CardStats, CardType


class Charm(Card):
    """Simplified Charm implemented as a Treasure providing economy."""

    def __init__(self):
        super().__init__(
            name="Charm",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.TREASURE],
        )
