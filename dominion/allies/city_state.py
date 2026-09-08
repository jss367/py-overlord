from .base_ally import Ally
from ..cards.allies._rules import decide


class CityState(Ally):
    def __init__(self):
        super().__init__("City-state")

    def _gain_zone(self, game_state, player, gained_card):
        if (
            player is not game_state.turn_player
            or not gained_card.is_action
            or player.favors < 2
        ):
            return None
        # Only the original gain destination is tracked; a reaction moving the
        # card elsewhere makes this play unavailable.
        zone = game_state.gain_destination(gained_card)
        if zone is None or gained_card not in zone:
            return None
        return zone

    def on_owner_gain_before_trait(self, game_state, player, gained_card):
        """Let the owner resolve City-state before Hasty moves the gain."""
        if (
            game_state.pile_trait(gained_card.name) != "Hasty"
            or self._gain_zone(game_state, player, gained_card) is None
            or not decide(
                game_state, player, "city_state_before_hasty", [False, True], True
            )
        ):
            return False
        self.on_owner_gain(game_state, player, gained_card)
        return True

    def on_owner_gain(self, game_state, player, gained_card):
        zone = self._gain_zone(game_state, player, gained_card)
        if zone is None:
            return
        if not decide(game_state, player, "city_state", [False, True], True):
            return
        player.favors -= 2
        game_state.play_action_from_zone_indirectly(player, gained_card, zone)
