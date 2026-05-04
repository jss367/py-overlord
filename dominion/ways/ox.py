"""Way of the Ox — +2 Actions."""

from .base_way import Way


class WayOfTheOx(Way):
    def __init__(self):
        super().__init__("Way of the Ox")

    def apply(self, game_state, card) -> None:
        game_state.current_player.actions += 2
