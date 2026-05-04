"""Way of the Sheep — +$2."""

from .base_way import Way


class WayOfTheSheep(Way):
    def __init__(self):
        super().__init__("Way of the Sheep")

    def apply(self, game_state, card) -> None:
        game_state.current_player.coins += 2
