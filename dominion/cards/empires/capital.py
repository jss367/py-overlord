from ..base_card import Card, CardCost, CardStats, CardType


class Capital(Card):
    """Simplified Capital that provides a burst of coins."""

    def __init__(self):
        super().__init__(
            name="Capital",
            cost=CardCost(coins=5),
            stats=CardStats(coins=6, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # Debt mechanics are not modelled; no extra handling required.
        pass
