"""Implementation of Farm (formerly Harem)."""

from ..base_card import Card, CardCost, CardStats, CardType


class Farm(Card):
    """Treasure-Victory: $2; 2 VP."""

    def __init__(self):
        super().__init__(
            name="Farm",
            cost=CardCost(coins=6),
            stats=CardStats(coins=2, vp=2),
            types=[CardType.TREASURE, CardType.VICTORY],
        )
