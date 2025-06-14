from ..base_card import Card, CardCost, CardStats, CardType

class Necropolis(Card):
    """Simple implementation of the Necropolis shelter."""

    def __init__(self):
        super().__init__(
            name="Necropolis",
            cost=CardCost(coins=0),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def starting_supply(self, game_state) -> int:
        # Shelters are not part of the normal supply
        return 0


class Hovel(Card):
    """Simple implementation of the Hovel shelter."""

    def __init__(self):
        super().__init__(
            name="Hovel",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.REACTION],
        )

    def starting_supply(self, game_state) -> int:
        return 0


class OvergrownEstate(Card):
    """Simple implementation of the Overgrown Estate shelter."""

    def __init__(self):
        super().__init__(
            name="Overgrown Estate",
            cost=CardCost(coins=0),
            stats=CardStats(vp=1),
            types=[CardType.VICTORY],
        )

    def starting_supply(self, game_state) -> int:
        return 0
