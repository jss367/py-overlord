"""Warlord counts cards in play, independently of pending Duration effects."""

import pytest

from dominion.cards.registry import get_card
from tests.test_allies_printed_rules import play, state


@pytest.mark.parametrize("destination", ["trash", "supply", "hand"])
def test_warlord_ignores_persistent_duration_references_that_left_play(destination):
    s, p, _ = state()
    s.setup_supply([get_card("Hireling")])
    old = play(s, p, "Hireling")
    p.in_play.remove(old)
    if destination == "trash":
        s.trash_card(p, old)
    elif destination == "supply":
        s._restore_to_supply_pile(old)
    else:
        p.hand.append(old)
    assert old in p.duration
    p.warlord_restriction_count = 1
    for expected in [True, True, False]:
        hireling = get_card("Hireling")
        p.hand.append(hireling)
        assert s.play_action_from_hand_indirectly(p, hireling) is expected
    assert sum(c.name == "Hireling" for c in p.in_play) == 2
