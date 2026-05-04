"""Flourishing Trade Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class FlourishingTrade(Prophecy):
    name: str = "Flourishing Trade"
    description: str = (
        "While active: all cards cost $1 less (minimum $0). You can use "
        "remaining Action plays as extra Buys in the Buy phase."
    )

    def cost_modifier(self, game_state, player, card) -> int:
        # Per rulebook: cost lowering does not affect Event costs; this
        # method is only invoked for cards (events handle costs separately).
        return -1

    def on_turn_start(self, game_state, player) -> None:
        # Convert leftover Action plays into Buys at the buy phase. We do
        # this lazily via a player flag picked up in handle_buy_phase.
        player.flourishing_trade_active = True
