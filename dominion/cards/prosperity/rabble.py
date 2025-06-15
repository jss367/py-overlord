from ..base_card import Card, CardCost, CardStats, CardType


class Rabble(Card):
    def __init__(self):
        super().__init__(
            name="Rabble",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        # TODO: attack effect
        pass
