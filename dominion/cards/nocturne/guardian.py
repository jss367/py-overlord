"""Guardian — $2 Action-Night-Duration.

Until your next turn, when another player plays an Attack, it doesn't
affect you. At start of next turn, +$1.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Guardian(Card):
    def __init__(self):
        super().__init__(
            name="Guardian",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT, CardType.DURATION],
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
        player.coins += 1
        self.duration_persistent = False

    def react_to_attack(self, game_state, player, attacker, attack_card) -> bool:
        # Guardian in duration blocks attacks. We override here in case it's
        # also in hand (unusual), to provide consistent blocking behaviour.
        return True
