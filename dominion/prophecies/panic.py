"""Panic Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class Panic(Prophecy):
    name: str = "Panic"
    description: str = (
        "While active: when you play a Treasure, +1 Buy. When you would "
        "discard the Treasure from play, return it to its pile instead."
    )

    def on_play_treasure(self, game_state, player, card) -> None:
        player.buys += 1
        # Cleanup-time return is handled by GameState.handle_cleanup_phase
        # via the panic_active flag below.
        player.panic_active = True
