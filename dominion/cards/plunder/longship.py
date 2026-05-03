"""Longship from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Longship(Card):
    """$5 Action-Duration: +2 Actions; at start of next turn, +2 Cards."""

    def __init__(self):
        super().__init__(
            name="Longship",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        self.duration_persistent = False
