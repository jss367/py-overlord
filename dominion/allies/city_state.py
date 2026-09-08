from .base_ally import Ally
from ..cards.allies._rules import decide


class CityState(Ally):
    def __init__(self):
        super().__init__("City-state")

    def on_owner_gain(self, game_state, player, gained_card):
        if (
            player is not game_state.turn_player
            or not gained_card.is_action
            or player.favors < 2
        ):
            return
        # Only the original gain destination is tracked; a reaction moving the
        # card elsewhere makes this play unavailable.
        zone = game_state.gain_destination(gained_card)
        if zone is None or gained_card not in zone:
            return
        if not decide(game_state, player, "city_state", [False, True], True):
            return
        player.favors -= 2
        game_state.play_action_from_zone_indirectly(player, gained_card, zone)
