from .base_ally import Ally
from ..cards.allies._rules import candidates, cheaper, decide, effective_cost, gain


class ArchitectsGuild(Ally):
    def __init__(self):
        super().__init__("Architects' Guild")

    def on_owner_gain(self, game_state, player, gained_card):
        if player.favors < 2:
            return
        choices = candidates(
            game_state,
            predicate=lambda c: (
                not c.is_victory
                and cheaper(
                    effective_cost(game_state, c),
                    effective_cost(game_state, gained_card),
                )
            ),
        )
        if choices and decide(
            game_state, player, "architects_guild", [False, True], True
        ):
            player.favors -= 2
            gain(game_state, player, choices)
