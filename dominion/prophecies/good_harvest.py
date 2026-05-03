"""Good Harvest Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class GoodHarvest(Prophecy):
    name: str = "Good Harvest"
    description: str = (
        "While active: the first time you play a Treasure each turn, "
        "+1 Buy and +$1."
    )

    def on_turn_start(self, game_state, player) -> None:
        player.good_harvest_used_this_turn = False

    def on_play_treasure(self, game_state, player, card) -> None:
        if not getattr(player, "good_harvest_used_this_turn", False):
            player.good_harvest_used_this_turn = True
            player.coins += 1
            player.buys += 1
