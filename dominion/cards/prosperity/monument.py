from ..base_card import Card, CardCost, CardStats, CardType


class Monument(Card):
    def __init__(self):
        super().__init__(
            name="Monument",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: gain a victory token
        pass
