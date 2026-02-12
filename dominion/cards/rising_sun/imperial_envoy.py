from ..base_card import Card, CardCost, CardStats, CardType


class ImperialEnvoy(Card):
    def __init__(self):
        super().__init__(
            name="Imperial Envoy",
            cost=CardCost(coins=5),
            stats=CardStats(cards=5, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.debt += 2
