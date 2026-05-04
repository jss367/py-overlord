from ..base_card import Card, CardCost, CardStats, CardType


class FishingVillage(Card):
    """Action-Duration ($3): +2 Actions, +$1. At the start of your next turn:
    +1 Action, +$1.
    """

    def __init__(self):
        super().__init__(
            name="Fishing Village",
            cost=CardCost(coins=3),
            stats=CardStats(actions=2, coins=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.actions += 1
        player.coins += 1
        self.duration_persistent = False
