# dominion/cards/registry.py
from typing import Dict, Type

from dominion.cards.base_card import Card
from dominion.cards.treasures import Copper, Silver, Gold
from dominion.cards.victory import Estate, Duchy, Province, Curse
from dominion.cards.base_set import (
    Village, Smithy, Market, Festival, Laboratory, 
    Mine, Witch, Moat, Workshop, Chapel
)

# Updated registry of all card types
CARD_TYPES: Dict[str, Type[Card]] = {
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

# Need to update base_card.py to support 'get_card' method
def get_card_by_name(name: str) -> Card:
    """Get a new instance of a card by name."""
    return get_card(name)
