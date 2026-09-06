"""Way of the Turtle — Set this aside; play it at start of next turn."""

from .base_way import Way


class WayOfTheTurtle(Way):
    def __init__(self):
        super().__init__("Way of the Turtle")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        # "Set this aside. If you did, play it at the start of your next
        # turn." A card that is not in play cannot be set aside: virtual
        # plays (Riverboat, Necromancer, Captain's Supply proxy) stay where
        # they are, and a Throne Room replay of a card an earlier Turtle
        # already stashed must not stash it a second time.
        if card not in player.in_play:
            return
        player.in_play.remove(card)
        # Leaving play ends any Frog marker from an earlier play this turn.
        card._frog_topdeck = None
        if not hasattr(player, "turtle_set_aside"):
            player.turtle_set_aside = []
        player.turtle_set_aside.append(card)
