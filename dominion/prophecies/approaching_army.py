"""Approaching Army Prophecy."""

from dataclasses import dataclass, field

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class ApproachingArmy(Prophecy):
    name: str = "Approaching Army"
    description: str = (
        "Setup: add an Attack pile to the Supply. While active: +$1 from each "
        "Attack card you play."
    )

    def setup(self, game_state) -> None:
        from dominion.cards.registry import CARD_TYPES, get_card

        existing = set(game_state.supply.keys())
        for name in CARD_TYPES.keys():
            if name in existing:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_attack:
                continue
            if getattr(card, "is_event", False) or getattr(card, "is_project", False):
                continue
            if card.cost.potions > 0:
                continue
            game_state.supply[card.name] = card.starting_supply(game_state)
            game_state.log_callback(
                f"Approaching Army adds Attack pile: {card.name}"
            )
            return

    def on_play_attack(self, game_state, player, card) -> None:
        player.coins += 1
