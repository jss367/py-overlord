from typing import Type

from dominion.cards.base_card import Card
from dominion.cards.base_set import Chapel, Festival, Laboratory, Market, Mine, Moat, Smithy, Village, Witch, Workshop
from dominion.cards.treasures import Copper, Gold, Silver
from dominion.cards.victory import Curse, Duchy, Estate, Province

# Updated registry of all card types
CARD_TYPES: dict[str, Type[Card]] = {
    # Treasure cards
    "Copper": Copper,
    "Silver": Silver,
    "Gold": Gold,
    # Victory cards
    "Estate": Estate,
    "Duchy": Duchy,
    "Province": Province,
    "Curse": Curse,
    # Action cards
    "Village": Village,
    "Smithy": Smithy,
    "Market": Market,
    "Festival": Festival,
    "Laboratory": Laboratory,
    "Mine": Mine,
    "Witch": Witch,
    "Moat": Moat,
    "Workshop": Workshop,
    "Chapel": Chapel,
}


def get_card(name: str) -> Card:
    """Get a new instance of a card by name."""
    if name not in CARD_TYPES:
        raise ValueError(f"Unknown card: {name}")
    return CARD_TYPES[name]()
