"""Bureaucracy Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class Bureaucracy(Prophecy):
    name: str = "Bureaucracy"
    description: str = (
        "While active: when you gain a card with $ in its cost (cost.coins>0 "
        "and not pure-Debt), gain a Copper."
    )

    def on_gain(self, game_state, player, card) -> None:
        from dominion.cards.registry import get_card

        if card.name == "Copper":
            return
        if card.cost.coins <= 0:
            # Pure-Debt cost cards (or $0 cards) don't trigger Bureaucracy.
            return
        if game_state.supply.get("Copper", 0) <= 0:
            return
        game_state.supply["Copper"] -= 1
        game_state.gain_card(player, get_card("Copper"))
