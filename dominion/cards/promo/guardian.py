from ..base_card import Card, CardCost, CardStats, CardType


class Guardian(Card):
    def __init__(self):
        super().__init__(
            name="Guardian",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.guardian_active = True
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 1
        player.guardian_active = False
        self.duration_persistent = False

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if self in player.discard:
            player.discard.remove(self)
            player.hand.append(self)
        elif self in player.deck:
            player.deck.remove(self)
            player.hand.append(self)
