"""Haunted Woods (Adventures) — $5 Action-Attack-Duration."""

from ..base_card import Card, CardCost, CardStats, CardType


class HauntedWoods(Card):
    def __init__(self):
        super().__init__(
            name="Haunted Woods",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            target.haunted_woods_attacks += 1

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target, attacker=player, attack_card=self)

        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 3)
        # Effect on opponents already cleared by their start-of-turn reset.
        self.duration_persistent = False
