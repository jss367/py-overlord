from .base_ally import Ally
from ..cards.allies._rules import decide


class IslandFolk(Ally):
    def __init__(self):
        super().__init__("Island Folk")

    def on_turn_end(self, game_state, player):
        if (
            player.favors < 5
            or player.took_extra_turn_last_turn
            or player.outpost_taken_last_turn
            or game_state.extra_turn
            or player.outpost_pending
        ):
            return
        if decide(game_state, player, "island_folk", [False, True], True):
            player.favors -= 5
            game_state.extra_turn = True
