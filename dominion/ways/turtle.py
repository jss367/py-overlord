"""Way of the Turtle — Set this aside; play it at start of next turn."""

from .base_way import Way


class WayOfTheTurtle(Way):
    def __init__(self):
        super().__init__("Way of the Turtle")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        # Remove the just-played card from in_play and stash it for next turn.
        if card in player.in_play:
            player.in_play.remove(card)
        if not hasattr(player, "turtle_set_aside"):
            player.turtle_set_aside = []
        player.turtle_set_aside.append(card)
