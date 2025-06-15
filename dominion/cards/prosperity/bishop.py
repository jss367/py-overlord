from ..base_card import Card, CardCost, CardStats, CardType


class Bishop(Card):
    """Simplified Bishop card."""

    def __init__(self):
        super().__init__(
            name="Bishop",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: implement trash for VP tokens
        pass
