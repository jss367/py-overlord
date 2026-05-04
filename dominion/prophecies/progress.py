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
        # Move from wherever the gain landed to the top of the deck.
        for zone in (player.discard, player.hand, player.deck):
            if card in zone and zone is not player.deck:
                zone.remove(card)
                player.deck.append(card)
                return
        # Already on the deck (e.g. via insignia / royal seal)? Re-place it
        # on top in case it was placed at the bottom.
        if card in player.deck:
            player.deck.remove(card)
            player.deck.append(card)
