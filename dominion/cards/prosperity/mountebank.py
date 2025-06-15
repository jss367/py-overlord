from ..base_card import Card, CardCost, CardStats, CardType


class Mountebank(Card):
    def __init__(self):
        super().__init__(
            name="Mountebank",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        # TODO: give others Curse and Copper unless they discard a Curse
        pass
