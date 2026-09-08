from .base_ally import Ally
from ..cards.allies._rules import candidates, decide, gain
from ..cards.base_card import CardCost


class CraftersGuild(Ally):
    def __init__(self):
        super().__init__("Crafters' Guild")

    def on_turn_start(self, game_state, player):
        if player.favors < 2:
            return
        choices = candidates(game_state, CardCost(coins=4))
        if choices and decide(
            game_state, player, "crafters_guild", [False, True], True
        ):
            player.favors -= 2
            gain(game_state, player, choices, to_deck=True)
