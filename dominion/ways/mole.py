"""Way of the Mole — +1 Action +3 Cards. Discard your hand."""

from .base_way import Way


class WayOfTheMole(Way):
    def __init__(self):
        super().__init__("Way of the Mole")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        player.actions += 1
        if player.hand:
            cards_to_discard = list(player.hand)
            player.hand = []
            game_state.discard_cards(player, cards_to_discard)
        game_state.draw_cards(player, 3)
