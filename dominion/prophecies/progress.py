"""Progress Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class Progress(Prophecy):
    name: str = "Progress"
    description: str = (
        "While active: when you gain a card, put it on top of your deck."
    )

    def on_gain(self, game_state, player, card) -> None:
        if game_state._remove_gained_card_from_zones(player, card, target=player.deck):
            game_state._cover_gained_deck_top(player, card)
            player.deck.append(card)
