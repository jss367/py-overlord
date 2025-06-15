from ..base_card import Card, CardCost, CardStats, CardType


class Expand(Card):
    def __init__(self):
        super().__init__(
            name="Expand",
            cost=CardCost(coins=7),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: trash a card to gain one costing up to 3 more
        pass
