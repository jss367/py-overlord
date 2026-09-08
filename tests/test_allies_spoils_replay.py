"""Replaying a Treasure repeats its instructions without returning it twice."""

import pytest

from dominion.cards.registry import get_card
from tests.test_allies_printed_rules import play, state


@pytest.mark.parametrize("multiplier,repeats", [("Specialist", 2), ("King's Cache", 3)])
def test_replayed_spoils_returns_only_once(multiplier, repeats):
    s, p, _ = state()
    s.supply = {"Spoils": 15}
    s.non_supply_pile_names = {"Spoils"}
    spoils = get_card("Spoils")
    p.hand = [spoils]
    multiplier_card = play(s, p, multiplier)
    assert p.coins - multiplier_card.stats.coins == 3 * repeats
    assert s.supply["Spoils"] == 16
    assert spoils not in p.in_play + p.hand + p.discard
    assert spoils not in p.all_cards()
