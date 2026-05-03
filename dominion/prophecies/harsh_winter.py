"""Harsh Winter Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class HarshWinter(Prophecy):
    name: str = "Harsh Winter"
    description: str = (
        "While active: when you gain a card on your turn, if there's Debt on "
        "its pile, take it; otherwise put 2 Debt on its pile. Off-turn gains "
        "neither place nor take Debt."
    )

    def on_gain(self, game_state, player, card) -> None:
        # Per rulebook clarification: "When it's not your turn, gaining a
        # card neither puts on the pile nor removes from the pile."
        if player is not game_state.current_player:
            return

        pile_name = card.name
        tokens = game_state.harsh_winter_debt.get(pile_name, 0)
        if tokens > 0:
            del game_state.harsh_winter_debt[pile_name]
            player.debt += tokens
        else:
            game_state.harsh_winter_debt[pile_name] = 2
