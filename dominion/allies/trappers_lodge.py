from .base_ally import Ally
from ..cards.allies._rules import decide


class TrappersLodge(Ally):
    """When you gain a card, may spend 1 Favor to topdeck it."""

    def __init__(self):
        super().__init__("Trappers' Lodge")

    def on_owner_gain(self, game_state, player, gained_card) -> None:
        if player.favors < 1:
            return
        zone = game_state.gain_destination(gained_card)
        movable = zone is not None and gained_card in zone and (
            zone is not player.deck or zone[-1] is gained_card
        )
        default = movable and gained_card.cost.coins >= 3 and not (
            gained_card.is_victory and not gained_card.is_action
        )
        if not decide(game_state, player, "trappers_lodge", [False, True], default):
            return
        player.favors -= 1
        # Spending is legal even if an earlier effect moved the gain. Never
        # follow it to another zone, or remove it from underneath a deck card.
        if movable and zone is not player.deck and game_state._remove_gained_card_from_zones(player, gained_card):
            game_state._cover_gained_deck_top(player, gained_card)
            player.deck.append(gained_card)
        game_state.log_callback(
            ("action", player.ai.name, f"spends 1 Favor on Trappers' Lodge for {gained_card}",
             {"favors_remaining": player.favors})
        )
