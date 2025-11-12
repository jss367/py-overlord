"""Tests to ensure the card registry does not contain improper entries."""

from dominion.cards.registry import CARD_TYPES, get_all_card_names, get_card


def test_registry_keys_match_card_names():
    """Every registered card key should match the instantiated card's name."""

    for name, cls in CARD_TYPES.items():
        card = cls()
        assert card.name == name


def test_get_all_card_names_are_unique():
    """The registry should not expose duplicate card names."""

    names = get_all_card_names()
    assert len(names) == len(set(names))


def test_card_aliases_resolve_to_canonical_names():
    """Aliases should resolve to the expected canonical card names."""

    aliases = {
        "Council room": "Council Room",
        "Throne room": "Throne Room",
        "Candlestick maker": "Candlestick Maker",
        "Poor house": "Poor House",
        "City quarter": "City Quarter",
        "Merchant guild": "Merchant Guild",
        "Wealthy village": "Wealthy Village",
        "Trading post": "Trading Post",
        "Native village": "Native Village",
    }

    for alias, canonical in aliases.items():
        card = get_card(alias)
        assert card.name == canonical
