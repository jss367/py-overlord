"""Harsh Winter Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class HarshWinter(Prophecy):
    name: str = "Harsh Winter"
    description: str = (
        "While active: when you gain a card on someone else's turn, put a "
        "Debt token on its pile. When you gain a card with Debt in its cost, "
        "remove all Debt tokens from its pile and take that much Debt."
    )

    def on_gain(self, game_state, player, card) -> None:
        pile_name = card.name
        # Off-turn gain → add a debt token to the pile
        if player is not game_state.current_player:
            game_state.harsh_winter_debt[pile_name] = (
                game_state.harsh_winter_debt.get(pile_name, 0) + 1
            )
            return

        # On-turn gain of a card whose cost has debt → take pile's debt
        if card.cost.debt > 0 and game_state.harsh_winter_debt.get(pile_name, 0) > 0:
            tokens = game_state.harsh_winter_debt.pop(pile_name)
            player.debt += tokens
