from .base_ally import Ally
from ..cards.allies._rules import decide, discard


class GangOfPickpockets(Ally):
    def __init__(self):
        super().__init__("Gang of Pickpockets")

    def on_turn_start(self, game_state, player):
        if player.favors and decide(
            game_state,
            player,
            "gang_of_pickpockets",
            [False, True],
            len(player.hand) > 4,
        ):
            player.favors -= 1
        else:
            discard(
                game_state, player, max(0, len(player.hand) - 4), "gang_of_pickpockets"
            )
