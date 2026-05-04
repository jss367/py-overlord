"""Biding Time Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class BidingTime(Prophecy):
    name: str = "Biding Time"
    description: str = (
        "While active: instead of discarding unplayed cards in Clean-up, set "
        "them aside; put them back into your hand at the start of your next turn."
    )

    def on_cleanup_start(self, game_state, player) -> None:
        # Move all hand cards to a side stash to be returned next turn.
        player.biding_time_set_aside.extend(player.hand)
        player.hand = []

    def on_turn_start(self, game_state, player) -> None:
        if player.biding_time_set_aside:
            player.hand.extend(player.biding_time_set_aside)
            player.biding_time_set_aside = []
