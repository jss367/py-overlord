"""Rapid Expansion Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class RapidExpansion(Prophecy):
    name: str = "Rapid Expansion"
    description: str = (
        "While active: when you gain an Action or Treasure card, set it aside "
        "and play it at the start of your next turn."
    )

    def on_gain(self, game_state, player, card) -> None:
        from dominion.cards.gain_decisions import gained_card_types
        action, treasure, _ = gained_card_types(game_state, player, card)
        if not (action or treasure):
            return
        if game_state._remove_gained_card_from_zones(player, card):
            player.rapid_expansion_set_aside.append(card)

    def on_turn_start(self, game_state, player) -> None:
        if not player.rapid_expansion_set_aside:
            return
        cards = list(player.rapid_expansion_set_aside)
        player.rapid_expansion_set_aside = []
        for card in cards:
            player.in_play.append(card)
            card.on_play(game_state)
