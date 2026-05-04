from ..base_card import Card, CardCost, CardStats, CardType


class MerchantShip(Card):
    """Action-Duration ($5): Now and at the start of your next turn: +$2."""

    def __init__(self):
        super().__init__(
            name="Merchant Ship",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 2
        self.duration_persistent = False
