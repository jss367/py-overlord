"""Implementation of the Trickster attack."""

from ..base_card import Card, CardCost, CardStats, CardType


class Trickster(Card):
    def __init__(self):
        super().__init__(
            name="Trickster",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.trickster_triggers_available += 1
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                game_state.give_curse_to_player(target)

            game_state.attack_player(other, attack)
