"""Werewolf — $5 Action-Night.

If played in Action phase: +3 Cards.
If played in Night phase: each other player receives a Hex.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Werewolf(Card):
    def __init__(self):
        super().__init__(
            name="Werewolf",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT, CardType.DOOM],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Determine current phase
        phase = game_state.phase
        if phase == "night":
            # Attack phase
            for other in game_state.players:
                if other is player:
                    continue

                def attack(target):
                    game_state.give_hex_to_player(target)

                game_state.attack_player(other, attack, attacker=player, attack_card=self)
        else:
            # Action phase: +3 Cards
            game_state.draw_cards(player, 3)
