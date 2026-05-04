"""Bard — $4 Action: +$2. Receive a Boon."""

from ..base_card import Card, CardCost, CardStats, CardType


class Bard(Card):
    uses_boons = True

    def __init__(self):
        super().__init__(
            name="Bard",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.FATE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.receive_boon(player)
