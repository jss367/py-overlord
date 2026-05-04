from .base_ally import Ally


class BandOfNomads(Ally):
    """When you gain a card costing $3+, you may spend a Favor for +1 Card,
    +1 Action, or +1 Buy.
    """

    def __init__(self):
        super().__init__("Band of Nomads")

    def on_owner_gain(self, game_state, player, gained_card) -> None:
        if player.favors <= 0:
            return
        if gained_card.cost.coins < 3:
            return
        # Prefer +1 Action when starved, else +1 Card, else +1 Buy.
        if player.actions == 0 and player.hand:
            player.actions += 1
            mode = "+1 Action"
        elif len(player.hand) <= 4:
            game_state.draw_cards(player, 1)
            mode = "+1 Card"
        elif player.buys < 2 and player.coins >= 3:
            player.buys += 1
            mode = "+1 Buy"
        else:
            # Don't spend a Favor when no mode is clearly useful.
            return
        player.favors -= 1
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends a Favor on Band of Nomads ({mode})",
                {"favors_remaining": player.favors},
            )
        )
