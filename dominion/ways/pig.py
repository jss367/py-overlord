"""Way of the Pig — +1 Card +1 Action."""

from .base_way import Way


class WayOfThePig(Way):
    def __init__(self):
        super().__init__("Way of the Pig")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        player.actions += 1
