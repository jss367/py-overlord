"""Way of the Mule — +1 Action +$1."""

from .base_way import Way


class WayOfTheMule(Way):
    def __init__(self):
        super().__init__("Way of the Mule")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        player.actions += 1
        player.coins += 1
