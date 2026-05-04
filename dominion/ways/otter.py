"""Way of the Otter — +2 Cards."""

from .base_way import Way


class WayOfTheOtter(Way):
    def __init__(self):
        super().__init__("Way of the Otter")

    def apply(self, game_state, card) -> None:
        game_state.draw_cards(game_state.current_player, 2)
