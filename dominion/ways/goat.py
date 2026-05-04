"""Way of the Goat — Trash a card from your hand."""

from .base_way import Way


class WayOfTheGoat(Way):
    def __init__(self):
        super().__init__("Way of the Goat")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        game_state.trash_card(player, choice)
