from ..base_card import Card, CardCost, CardStats, CardType


class Fortune(Card):
    def __init__(self):
        super().__init__(
            name="Fortune",
            cost=CardCost(debt=8),
            stats=CardStats(buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.coins *= 2
