"""Ghost Town — $3 Action-Night-Duration.

+1 Card +1 Action. When you gain this, put it into hand.
(Per the spec: it provides +1 Card +1 Action at the start of your next turn.)
"""

from ..base_card import Card, CardCost, CardStats, CardType


class GhostTown(Card):
    def __init__(self):
        super().__init__(
            name="Ghost Town",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT, CardType.DURATION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
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
        game_state.draw_cards(player, 1)
        if not player.ignore_action_bonuses:
            player.actions += 1
        self.duration_persistent = False
