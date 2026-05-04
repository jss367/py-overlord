"""Cursed Village — $5 Action.

+2 Actions. Draw until you have 6 in hand. Receive a Hex.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class CursedVillage(Card):
    def __init__(self):
        super().__init__(
            name="Cursed Village",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2),
            types=[CardType.ACTION, CardType.DOOM],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        deficit = max(0, 6 - len(player.hand))
        if deficit:
            game_state.draw_cards(player, deficit)
        game_state.give_hex_to_player(player)
