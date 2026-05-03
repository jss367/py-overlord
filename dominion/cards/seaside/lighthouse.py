from ..base_card import Card, CardCost, CardStats, CardType


class Lighthouse(Card):
    """Action-Duration ($2): +1 Action, +$1. Now and at the start of your next turn:
    +$1. Until then, when another player plays an Attack card, it doesn't affect you.
    """

    def __init__(self):
        super().__init__(
            name="Lighthouse",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 1
        self.duration_persistent = False
