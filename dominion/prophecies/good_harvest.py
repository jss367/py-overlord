"""Good Harvest Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class GoodHarvest(Prophecy):
    name: str = "Good Harvest"
    description: str = (
        "While active: the first time you play each differently named "
        "Treasure each turn, +1 Buy and +$1."
    )

    def on_turn_start(self, game_state, player) -> None:
        player.good_harvest_treasures_played = set()

    def on_play_treasure(self, game_state, player, card) -> None:
        seen = getattr(player, "good_harvest_treasures_played", None)
        if seen is None:
            seen = set()
            player.good_harvest_treasures_played = seen
        if card.name in seen:
            return
        seen.add(card.name)
        player.coins += 1
        player.buys += 1
