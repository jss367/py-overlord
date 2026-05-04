"""Swamp Hag (Adventures) — $5 Action-Attack-Duration."""

from ..base_card import Card, CardCost, CardStats, CardType


class SwampHag(Card):
    def __init__(self):
        super().__init__(
            name="Swamp Hag",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            target.swamp_hag_attacks += 1

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target, attacker=player, attack_card=self)

        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 3
        self.duration_persistent = False
