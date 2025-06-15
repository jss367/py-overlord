from ..base_card import Card, CardCost, CardStats, CardType


class KingsCourt(Card):
    def __init__(self):
        super().__init__(
            name="King's Court",
            cost=CardCost(coins=7),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: play an action card three times
        pass
