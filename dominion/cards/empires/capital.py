from ..base_card import Card, CardCost, CardStats, CardType


class Capital(Card):
    """Capital Treasure that imposes debt when it leaves play."""

    def __init__(self):
        super().__init__(
            name="Capital",
            cost=CardCost(coins=5),
            stats=CardStats(coins=6, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        pass
