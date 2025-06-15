from ..base_card import Card, CardCost, CardStats, CardType


class CountingHouse(Card):
    def __init__(self):
        super().__init__(
            name="Counting House",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: draw coppers from discard
        pass
