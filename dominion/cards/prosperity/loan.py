from ..base_card import Card, CardCost, CardStats, CardType


class Loan(Card):
    def __init__(self):
        super().__init__(
            name="Loan",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        # TODO: reveal cards until a treasure is revealed and trash it
        pass
