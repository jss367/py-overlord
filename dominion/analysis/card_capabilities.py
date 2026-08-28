"""Declarative card capability metadata.

``CardStats`` covers cards whose contribution is printed as flat numbers
(+2 Actions, +3 Cards). Cards whose real contribution is computed inside
``play_effect`` — Magnate's per-Treasure draw, Bank's per-Treasure coins,
King's Court's triple play — read as all-zero stats, which left role
inference blind to exactly the cards strong engines are built around
(the Oslo board's winning Workers' Village/Magnate engine was
unsearchable partly because Magnate classified as a no-stat terminal).

This module layers a small hand-annotated override table on top of the
static stats and exposes one query point, :func:`capabilities_for`. The
table is deliberately incremental: any card absent from it falls back to
its printed stats, so annotating a card is only required when its stats
lie about what it does. ``draw`` and ``coins`` are *expected values per
play* for dynamic cards — coarse estimates are fine; they only need to
put the card in the right role bucket, not price it exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dominion.cards.registry import get_card


@dataclass(frozen=True)
class CardCapabilities:
    """What one card contributes to a deck, dynamic effects included."""

    name: str
    cost: int
    actions: int
    draw: float   # expected cards drawn per play
    coins: float  # expected coins produced per play
    buys: int
    is_action: bool
    is_treasure: bool
    is_gainer: bool      # gains extra cards during play or on a play trigger
    is_multiplier: bool  # plays another Action card multiple times
    is_trasher: bool     # trashes cards from the player's own deck
    is_attack: bool


# Hand-annotated corrections for cards whose CardStats misrepresent their
# in-play contribution. Keys are the fields of CardCapabilities to override.
_OVERRIDES: dict[str, dict] = {
    # Dynamic draw.
    "Magnate": {"draw": 3.0},          # reveal hand, +1 Card per Treasure
    "Watchtower": {"draw": 2.0},       # draw until 6 cards in hand
    "Adventurer": {"draw": 2.0},       # dig for two Treasures
    "Jack of All Trades": {"draw": 1.0, "is_gainer": True},  # draw to 5, gain Silver
    # Dynamic coins.
    "Bank": {"coins": 3.0},            # $1 per Treasure in play, itself included
    # Multipliers.
    "Throne Room": {"is_multiplier": True},
    "King's Court": {"is_multiplier": True},
    # Gainers / remodelers.
    "Workshop": {"is_gainer": True},
    "Feast": {"is_gainer": True},
    "Bureaucrat": {"is_gainer": True},  # gains a Silver to the deck
    "Anvil": {"is_gainer": True},       # discard a Treasure, gain up to $4
    "Remodel": {"is_gainer": True, "is_trasher": True},
    "Expand": {"is_gainer": True, "is_trasher": True},
    "Mine": {"is_gainer": True, "is_trasher": True},
    # Pure trashers.
    "Chapel": {"is_trasher": True},
}


def capabilities_for(name: str) -> Optional[CardCapabilities]:
    """Return the capabilities of ``name``, or ``None`` for unknown cards."""

    try:
        card = get_card(name)
    except (KeyError, ValueError):
        return None

    fields = {
        "name": card.name,
        "cost": card.cost.coins,
        "actions": card.stats.actions,
        "draw": float(card.stats.cards),
        "coins": float(card.stats.coins),
        "buys": card.stats.buys,
        "is_action": card.is_action,
        "is_treasure": card.is_treasure,
        "is_gainer": False,
        "is_multiplier": False,
        "is_trasher": False,
        "is_attack": card.is_attack,
    }
    fields.update(_OVERRIDES.get(card.name, {}))
    return CardCapabilities(**fields)


def kingdom_capabilities(kingdom_cards: list[str]) -> dict[str, CardCapabilities]:
    """Capabilities for every resolvable kingdom card, keyed by canonical name.

    Boards may spell cards through registry aliases ("Wealthy village");
    keys are always ``CardCapabilities.name`` — the canonical registry
    spelling — so lookups by a capability object's ``name`` never miss.
    """

    out: dict[str, CardCapabilities] = {}
    for name in kingdom_cards:
        caps = capabilities_for(name)
        if caps is not None:
            out[caps.name] = caps
    return out
