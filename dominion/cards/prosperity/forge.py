from ..base_card import Card, CardCost, CardStats, CardType


class Forge(Card):
    def __init__(self):
        super().__init__(
            name="Forge",
            cost=CardCost(coins=7),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: trash cards to gain one costing exact total
        pass
