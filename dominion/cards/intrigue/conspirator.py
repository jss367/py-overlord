"""Implementation of the Conspirator card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Conspirator(Card):
    def __init__(self):
        super().__init__(
            name="Conspirator",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if player.actions_this_turn >= 3:
            game_state.draw_cards(player, 1)
            player.actions += 1
