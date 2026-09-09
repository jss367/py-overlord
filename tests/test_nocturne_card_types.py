"""Printed types from the official Nocturne rulebook, pages 5–10.

https://www.riograndegames.com/wp-content/uploads/2017/08/Dominion-Nocturne-Rules.pdf
"""

import pytest

from dominion.cards.registry import get_all_card_names, get_card


EXPECTED_TYPES = {
    "Bat": {"night"},
    "Changeling": {"night"},
    "Cobbler": {"night", "duration"},
    "Crypt": {"night", "duration"},
    "Den of Sin": {"night", "duration"},
    "Devil's Workshop": {"night"},
    "Exorcist": {"night"},
    "Ghost": {"night", "duration", "spirit"},
    "Ghost Town": {"night", "duration"},
    "Guardian": {"night", "duration"},
    "Leprechaun": {"action", "doom"},
    "Monastery": {"night"},
    "Night Watchman": {"night"},
    "Raider": {"night", "duration", "attack"},
    "Vampire": {"night", "attack", "doom"},
    "Werewolf": {"action", "night", "attack", "doom"},
    "Zombie Mason": {"action", "zombie"},
}


@pytest.mark.parametrize("name, expected", EXPECTED_TYPES.items())
def test_printed_card_types(name, expected):
    assert {kind.value for kind in get_card(name).types} == expected


def test_registry_contains_exactly_the_official_night_cards():
    expected = {name for name, types in EXPECTED_TYPES.items() if "night" in types}
    actual = {name for name in get_all_card_names() if get_card(name).is_night}
    assert actual == expected
