from .base_ally import Ally


class GangOfPickpockets(Ally):
    """At start of turn, spend 1 Favor or discard a card."""

    def __init__(self):
        super().__init__("Gang of Pickpockets")

    def on_turn_start(self, game_state, player) -> None:
        # Always pay the toll. Spend a Favor when available; else
        # discard the worst card in hand.
        if player.favors > 0:
            player.favors -= 1
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    "spends a Favor on Gang of Pickpockets (toll)",
                    {"favors_remaining": player.favors},
                )
            )
            return
        if not player.hand:
            return
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 1, reason="gang_of_pickpockets"
        )
        if not picks:
            return
        target = picks[0]
        if target in player.hand:
            player.hand.remove(target)
            game_state.discard_card(player, target)
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"discards {target} for Gang of Pickpockets toll",
                    {},
                )
            )
