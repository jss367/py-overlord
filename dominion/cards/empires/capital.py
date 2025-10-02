from ..base_card import Card, CardCost, CardStats, CardType


class Capital(Card):
    """Simplified Capital Treasure that ignores debt effects."""

    def __init__(self):
        super().__init__(
            name="Capital",
            cost=CardCost(coins=5),
            stats=CardStats(coins=6, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        pass
