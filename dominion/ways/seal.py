"""Way of the Seal — +$1; this turn, when you gain a card, put it onto your deck."""

from .base_way import Way


class WayOfTheSeal(Way):
    def __init__(self):
        super().__init__("Way of the Seal")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        player.coins += 1
        player.topdeck_gains = True
