"""Way of the Frog — +1 Action. Topdeck this card on Cleanup."""

from .base_way import Way


class WayOfTheFrog(Way):
    def __init__(self):
        super().__init__("Way of the Frog")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        player.actions += 1
        # Mark the card so cleanup knows to topdeck it.
        card._frog_topdeck = True
