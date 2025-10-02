from ..base_card import Card, CardCost, CardStats, CardType


class Stash(Card):
    """Treasure that can be placed deliberately during shuffles."""

    def __init__(self):
        super().__init__(
            name="Stash",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )
