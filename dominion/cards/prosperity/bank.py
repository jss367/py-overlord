from ..base_card import Card, CardCost, CardStats, CardType


class Bank(Card):
    """Simplified implementation of the Bank card."""

    def __init__(self):
        super().__init__(
            name="Bank",
            cost=CardCost(coins=7),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        # TODO: add effect based on treasures in play
        pass
