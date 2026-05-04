from ..base_card import Card, CardCost, CardStats, CardType


class Necropolis(Card):
    """Necropolis shelter: +2 Actions."""

    def __init__(self):
        super().__init__(
            name="Necropolis",
            cost=CardCost(coins=1),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def starting_supply(self, game_state) -> int:
        return 0


class Hovel(Card):
    """Hovel shelter: when you buy a Victory card, you may trash this."""

    def __init__(self):
        super().__init__(
            name="Hovel",
            cost=CardCost(coins=1),
            stats=CardStats(),
            types=[CardType.REACTION],
        )

    def starting_supply(self, game_state) -> int:
        return 0


class OvergrownEstate(Card):
    """Overgrown Estate shelter: 0 VP. When trashed, +1 Card."""

    def __init__(self):
        super().__init__(
            name="Overgrown Estate",
            cost=CardCost(coins=1),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def starting_supply(self, game_state) -> int:
        return 0

    def get_victory_points(self, player) -> int:
        # Overgrown Estate is worth 0 VP (special card type, not 1).
        return 0

    def on_trash(self, game_state, player):
        game_state.draw_cards(player, 1)
