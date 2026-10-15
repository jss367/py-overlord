"""Den of Sin — $5 Night-Duration.

At start of next turn, +2 Cards. This is gained to your hand instead of your discard pile.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class DenOfSin(Card):
    default_gain_destination = "hand"

    def __init__(self):
        super().__init__(
            name="Den of Sin",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.NIGHT, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if self in player.in_play:
            player.in_play.remove(self)
        if self not in player.duration:
            player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        self.duration_persistent = False
