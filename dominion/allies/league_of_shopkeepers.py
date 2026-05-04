from .base_ally import Ally


class LeagueOfShopkeepers(Ally):
    """When you play a Liaison, +1 Favor; when 3+ Liaisons in play, +$1;
    when 5+, +1 Buy.
    """

    def __init__(self):
        super().__init__("League of Shopkeepers")

    def on_play_card(self, game_state, player, card) -> None:
        if not card.is_liaison:
            return
        # +1 Favor whenever you play a Liaison (this is a perk; the
        # Liaison itself also grants a Favor as part of its effect).
        player.favors += 1

        liaison_count = sum(
            1 for c in player.in_play if c.is_liaison
        )
        if liaison_count >= 3:
            player.coins += 1
        if liaison_count >= 5:
            player.buys += 1
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"League of Shopkeepers triggers ({liaison_count} Liaisons in play)",
                {"favors_remaining": player.favors},
            )
        )
