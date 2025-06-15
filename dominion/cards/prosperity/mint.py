from ..base_card import Card, CardCost, CardStats, CardType


class Mint(Card):
    def __init__(self):
        super().__init__(
            name="Mint",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: gain a copy of a treasure from hand
        pass

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        # TODO: trash all treasures you have in play
        pass
