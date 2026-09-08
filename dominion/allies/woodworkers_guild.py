from .base_ally import Ally
from ..cards.allies._rules import candidates, decide, gain


class WoodworkersGuild(Ally):
    def __init__(self):
        super().__init__("Woodworkers' Guild")

    def on_buy_phase_start(self, game_state, player):
        if not player.favors:
            return
        actions = [c for c in player.hand if c.is_action]
        default = min(actions, key=lambda c: c.cost.coins) if actions else None
        target = decide(
            game_state, player, "woodworkers_trash", [None] + actions, default
        )
        if target is None:
            return
        player.favors -= 1
        player.hand.remove(target)
        game_state.trash_card(player, target)
        gain(
            game_state, player, candidates(game_state, predicate=lambda c: c.is_action)
        )
