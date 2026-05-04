from .base_ally import Ally


class MountainFolk(Ally):
    """At start of turn, you may spend 5 Favors for +3 Cards."""

    def __init__(self):
        super().__init__("Mountain Folk")

    def on_turn_start(self, game_state, player) -> None:
        if player.favors < 5:
            return
        player.favors -= 5
        game_state.draw_cards(player, 3)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                "spends 5 Favors on Mountain Folk (+3 Cards)",
                {"favors_remaining": player.favors},
            )
        )
