"""Way of the Squirrel — +2 Cards next turn."""

from .base_way import Way


class WayOfTheSquirrel(Way):
    def __init__(self):
        super().__init__("Way of the Squirrel")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        # Bank 2 cards to draw at start of next turn.
        player.squirrel_pending = getattr(player, "squirrel_pending", 0) + 2
