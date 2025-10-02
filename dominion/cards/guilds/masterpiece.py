from ..base_card import Card, CardCost, CardStats, CardType


class Masterpiece(Card):
    """Simple treasure representing the Guilds overpay card."""

    def __init__(self):
        super().__init__(
            name="Masterpiece",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )
