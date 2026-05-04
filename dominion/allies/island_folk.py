from .base_ally import Ally


class IslandFolk(Ally):
    """At end of turn, spend 5 Favors for an extra turn.

    Implementation: schedule via the existing Outpost mechanic
    (``player.outpost_pending``) which gives the player an extra turn
    with a 3-card hand. This is a slight nerf vs the official Island
    Folk extra-turn but matches the engine's existing extra-turn flow.
    """

    def __init__(self):
        super().__init__("Island Folk")

    def on_turn_end(self, game_state, player) -> None:
        if player.favors < 5:
            return
        if getattr(player, "outpost_taken_last_turn", False):
            return
        if getattr(player, "outpost_pending", False):
            return
        player.favors -= 5
        player.outpost_pending = True
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                "spends 5 Favors on Island Folk for an extra turn",
                {"favors_remaining": player.favors},
            )
        )
