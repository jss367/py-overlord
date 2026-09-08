from .base_ally import Ally
from ..cards.allies._rules import decide


class FamilyOfInventors(Ally):
    def __init__(self):
        super().__init__("Family of Inventors")

    def on_buy_phase_start(self, game_state, player):
        from ..cards.registry import get_card

        if player.favors < 1:
            return
        piles = [
            n for n in game_state.rotatable_supply_piles() if not get_card(n).is_victory
        ]
        default = max(piles, key=lambda n: get_card(n).cost.coins, default=None)
        choice = decide(
            game_state, player, "family_of_inventors_pile", [None] + piles, default
        )
        if choice is None:
            return
        player.favors -= 1
        if not hasattr(game_state, "family_inventor_tokens"):
            game_state.family_inventor_tokens = {}
        game_state.family_inventor_tokens[choice] = (
            game_state.family_inventor_tokens.get(choice, 0) + 1
        )
