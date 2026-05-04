"""Tracker — $2 Action.

+1 Action +$1. Receive a Boon. (Heirloom: Pouch.)
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Tracker(Card):
    heirloom = "Pouch"
    uses_boons = True

    def __init__(self):
        super().__init__(
            name="Tracker",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION, CardType.FATE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.receive_boon(player)
