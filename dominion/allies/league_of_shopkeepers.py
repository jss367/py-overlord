from .base_ally import Ally


class LeagueOfShopkeepers(Ally):
    """When you play a Liaison: +1 Favor; if you have 3+ Favors, +$1; if
    you have 5+ Favors, +1 Buy.

    The official rule keys the +$ / +Buy off the player's Favor count, not
    the number of Liaisons currently in play. Both bonuses fire (the Ally
    text reads "If you have 5 or more Favors, +1 Buy" with the +$ trigger
    on its own line).
    """

    def __init__(self):
        super().__init__("League of Shopkeepers")

    def on_play_card(self, game_state, player, card) -> None:
        if not card.is_liaison:
            return
        # +1 Favor whenever you play a Liaison (this is a perk; the
        # Liaison itself also grants a Favor as part of its effect).
        player.favors += 1

        favors = player.favors
        if favors >= 3:
            player.coins += 1
        if favors >= 5:
            player.buys += 1
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"League of Shopkeepers triggers ({favors} Favors)",
                {"favors_remaining": favors},
            )
        )
