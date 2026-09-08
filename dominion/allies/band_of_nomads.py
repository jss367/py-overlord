from .base_ally import Ally
from ..cards.allies._rules import decide, effective_cost


class BandOfNomads(Ally):
    def __init__(self):
        super().__init__("Band of Nomads")

    def on_owner_gain(self, game_state, player, gained_card):
        if player.favors < 1 or effective_cost(game_state, gained_card).coins < 3:
            return
        default = (
            "action"
            if player.actions == 0 and player.hand
            else "card"
            if len(player.hand) <= 4
            else None
        )
        mode = decide(
            game_state,
            player,
            "band_of_nomads",
            [None, "card", "action", "buy"],
            default,
        )
        if mode is None:
            return
        player.favors -= 1
        if mode == "card":
            game_state.draw_cards(player, 1)
        elif mode == "action" and not player.ignore_action_bonuses:
            player.actions += 1
        elif mode == "buy":
            player.buys += 1
