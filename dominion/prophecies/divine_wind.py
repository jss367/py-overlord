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

        # Per rulebook: only the Kingdom Supply piles used this game are
        # removed. Basic piles (Copper/Silver/Gold/Platinum, Estate/Duchy/
        # Province/Colony, Curse, Potion) and non-Kingdom support piles
        # (Ruins, Spoils, Horse, Madman, Mercenary, Loot, Bystander/Joust
        # rewards, etc.) stay — we identify the Kingdom piles by the snapshot
        # taken at initialize_game time.
        kingdom_pile_names = list(getattr(game_state, "original_kingdom_pile_names", set()))
        removed = []
        for name in kingdom_pile_names:
            if name in game_state.supply:
                del game_state.supply[name]
                removed.append(name)

        # Pick 10 fresh Kingdom-eligible cards not previously in the supply.
        previously_in_supply = set(removed) | set(game_state.supply.keys())
        candidates = []
        for name, cls in CARD_TYPES.items():
            if name in previously_in_supply:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if getattr(card, "is_event", False) or getattr(card, "is_project", False):
                continue
            # Skip pure Victory cards and Curses as Kingdom replacements.
            if card.is_victory and not card.is_action:
                continue
            if card.name == "Curse":
                continue
            candidates.append(card)

        random.shuffle(candidates)
        added = 0
        for card in candidates:
            if added >= 10:
                break
            game_state.supply[card.name] = card.starting_supply(game_state)
            # Track the new pile so a second Divine Wind (extremely unlikely)
            # would also remove it.
            game_state.original_kingdom_pile_names.add(card.name)
            added += 1
        game_state.log_callback(
            f"Divine Wind: replaced {len(removed)} Kingdom piles with {added} new ones"
        )
