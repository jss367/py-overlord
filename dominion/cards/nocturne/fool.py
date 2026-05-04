"""Fool — $3 Action.

If you don't have a Lost in the Woods (state), receive 3 Boons in any order
and take Lost in the Woods. (Heirloom: Lucky Coin.)
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Fool(Card):
    heirloom = "Lucky Coin"
    uses_boons = True

    def __init__(self):
        super().__init__(
            name="Fool",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.FATE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if getattr(player, "lost_in_the_woods", False):
            return
        for _ in range(3):
            game_state.receive_boon(player)
        player.lost_in_the_woods = True
