"""Den of Sin — $5 Action-Night-Duration.

At start of next turn, +2 Cards. When you gain this, put it into hand.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class DenOfSin(Card):
    def __init__(self):
        super().__init__(
            name="Den of Sin",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT, CardType.DURATION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        # Put the card into hand instead of discard
        if self in player.discard:
            player.discard.remove(self)
        elif self in player.deck:
            player.deck.remove(self)
        if self not in player.hand:
            player.hand.append(self)

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
