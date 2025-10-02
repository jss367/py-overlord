from ..base_card import Card, CardCost, CardStats, CardType


class Castle(Card):
    """Generic Castle victory card placeholder for the Castles pile."""

    def __init__(self):
        super().__init__(
            name="Castle",
            cost=CardCost(coins=6),
            stats=CardStats(vp=2),
            types=[CardType.VICTORY],
        )

    def starting_supply(self, game_state) -> int:
        # The Castles pile always contains the fixed stack of eight Castle cards
        return 8
