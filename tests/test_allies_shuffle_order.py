"""The owner orders simultaneous topdeck effects during a shuffle."""

from itertools import permutations

import pytest

from dominion.cards.registry import get_card
from dominion.projects.star_chart import StarChart
from dominion.traits import apply_trait
from tests.test_allies_interactions import ChoiceAI
from tests.test_allies_printed_rules import state


GROUPS = ("Fated", "Star Chart", "Order of Astrologers")


@pytest.mark.parametrize("placement_order", list(permutations(GROUPS)))
def test_astrologers_fated_and_star_chart_can_topdeck_in_any_order(placement_order):
    s, p, _ = state("Order of Astrologers")
    s.setup_supply([get_card("Town Crier")])
    apply_trait(s, "Fated", "Town Crier")
    p.projects = [StarChart()]
    p.favors = 2
    p.discard = [get_card(n) for n in [
        "Blacksmith", "Gold", "Town Crier", "Silver", "Smithy", "Curse"
    ]]
    originals = list(p.discard)

    class OrderedAI(ChoiceAI):
        def choose_allies_option(self, state, player, reason, options, default):
            if reason == "astrologers_topdeck":
                return next(c for n in ["Gold", "Silver"] for c in options if c.name == n)
            if reason == "shuffle_topdeck_next":
                return next(n for n in placement_order if n in options)
            return super().choose_allies_option(state, player, reason, options, default)

    p.ai = OrderedAI()
    p.shuffle_discard_into_deck()
    draw_groups = {
        "Fated": ["Town Crier", "Blacksmith"],
        "Star Chart": ["Smithy"],
        "Order of Astrologers": ["Gold", "Silver"],
    }
    expected = [n for group in reversed(placement_order) for n in draw_groups[group]]
    assert [c.name for c in reversed(p.deck)] == expected + ["Curse"]
    assert p.favors == 0
    assert p.discard == []
    assert sorted(map(id, p.all_cards())) == sorted(map(id, originals))


def test_invalid_shuffle_order_choice_keeps_the_default_placement_order():
    s, p, _ = state("Order of Astrologers")
    s.setup_supply([get_card("Village")])
    apply_trait(s, "Fated", "Village")
    p.favors = 1
    p.ai = ChoiceAI({"astrologers_topdeck": "Gold", "shuffle_topdeck_next": "invalid"})
    p.discard = [get_card("Village"), get_card("Gold")]
    p.shuffle_discard_into_deck()
    assert [c.name for c in reversed(p.deck)] == ["Gold", "Village"]
    assert p.favors == 0
