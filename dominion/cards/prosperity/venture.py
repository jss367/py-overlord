from ..base_card import Card, CardCost, CardStats, CardType


class Venture(Card):
    def __init__(self):
        super().__init__(
            name="Venture",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        # TODO: reveal cards until a treasure is revealed and play it
        pass
