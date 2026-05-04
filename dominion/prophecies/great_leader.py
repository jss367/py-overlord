"""Great Leader Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class GreatLeader(Prophecy):
    name: str = "Great Leader"
    description: str = (
        "While active: after each Action card you play, +1 Action."
    )

    def on_play_action(self, game_state, player, card) -> None:
        player.actions += 1
