from ..base_card import Card, CardCost, CardStats, CardType


class Nomads(Card):
    def __init__(self):
        super().__init__(
            name="Nomads",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        player.coins += 2

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        player.coins += 2
