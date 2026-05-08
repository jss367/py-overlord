"""Way of the Monkey — +1 Buy +$1."""

from .base_way import Way


class WayOfTheMonkey(Way):
    def __init__(self):
        super().__init__("Way of the Monkey")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        player.buys += 1
        player.coins += 1
