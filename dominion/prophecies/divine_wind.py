"""Divine Wind Prophecy."""

import random
from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class DivineWind(Prophecy):
    name: str = "Divine Wind"
    description: str = (
        "On activation: the 10 Kingdom Supply piles are removed, and 10 new "
        "Kingdom card piles are dealt out."
    )

    def on_activate(self, game_state) -> None:
        from dominion.cards.registry import CARD_TYPES, get_card

        protected = {
            "Copper", "Silver", "Gold", "Platinum",
            "Estate", "Duchy", "Province", "Colony",
            "Curse", "Potion",
        }
        # Anything that isn't a basic / non-supply pile is treated as a
        # Kingdom pile to remove.
        old_kingdom = [
            name for name in list(game_state.supply.keys())
            if name not in protected
        ]
        for name in old_kingdom:
            del game_state.supply[name]

        # Pick 10 fresh Kingdom-eligible cards not previously in the supply.
        candidates = []
        for name, cls in CARD_TYPES.items():
            if name in protected or name in old_kingdom:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if getattr(card, "is_event", False) or getattr(card, "is_project", False):
                continue
            if card.is_victory and not card.is_action:
                continue
            candidates.append(card)

        random.shuffle(candidates)
        added = 0
        for card in candidates:
            if added >= 10:
                break
            game_state.supply[card.name] = card.starting_supply(game_state)
            added += 1
        game_state.log_callback(
            f"Divine Wind: replaced {len(old_kingdom)} Kingdom piles with {added} new ones"
        )
