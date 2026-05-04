from .base_ally import Ally


class OrderOfMasons(Ally):
    """When you discard at end of turn, +1 Card per 2 Favors.

    Hooked at end-of-turn before the cleanup discard happens. We bank
    an extra-draw amount on the player and spend Favors; the cleanup
    will then draw the standard 5 plus this bonus via
    ``order_of_masons_bonus``.

    Implementation: convert immediately into +draws on the next-turn
    hand size by stashing a positive counter on the player. The
    ``handle_cleanup_phase`` already draws 5 cards; we extend the draw
    by ``order_of_masons_bonus`` and reset.
    """

    def __init__(self):
        super().__init__("Order of Masons")

    def on_turn_end(self, game_state, player) -> None:
        if player.favors < 2:
            return
        spend = min(player.favors // 2, 4)
        if spend <= 0:
            return
        player.favors -= spend * 2
        # Stash bonus draws to be applied on top of the next turn's hand.
        existing = getattr(player, "order_of_masons_bonus", 0)
        player.order_of_masons_bonus = existing + spend
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends {spend * 2} Favors on Order of Masons (+{spend} Cards)",
                {"favors_remaining": player.favors},
            )
        )
