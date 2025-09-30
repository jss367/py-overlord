"""Implementation of the Wharf duration card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Wharf(Card):
    def __init__(self):
        super().__init__(
            name="Wharf",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.buys += 1
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.buys += 1
        self.duration_persistent = False
