"""Way of the Owl — +1 Action. Draw until you have 6 cards in hand."""

from .base_way import Way


class WayOfTheOwl(Way):
    def __init__(self):
        super().__init__("Way of the Owl")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        player.actions += 1
        target = 6
        while len(player.hand) < target:
            drawn = game_state.draw_cards(player, 1)
            if not drawn:
                break
