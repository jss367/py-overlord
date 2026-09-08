"""Copy gains recheck the exposed physical pile after City-state plays."""

import pytest

from dominion.cards.registry import get_card
from tests.test_allies_interactions import ChoiceAI
from tests.test_allies_printed_rules import state


def enable_copy(s, p, effect):
    if effect == "Mirror":
        s.mirror_pending[id(p)] = 1
    else:
        p.tavern_mat = [get_card("Duplicate")]
        p.ai.should_call_from_tavern = lambda *args: True


@pytest.mark.parametrize("effect", ["Mirror", "Duplicate"])
@pytest.mark.parametrize("rotate", [False, True])
def test_copy_gain_cannot_take_card_buried_by_city_state(effect, rotate):
    s, p, _ = state("City-state")
    s.setup_supply([get_card("Town Crier")])
    p.ai = ChoiceAI({
        "city_state_before_gain_effects": True,
        "rotate_pile": "Town Crier" if rotate else None,
    })
    p.favors = 2
    enable_copy(s, p, effect)
    original = s.take_top_supply_card("Town Crier")
    s.gain_card(p, original)
    assert original in p.in_play
    assert s.top_supply_card("Town Crier") == ("Blacksmith" if rotate else "Town Crier")
    assert s.supply["Town Crier"] == (3 if rotate else 2)
    assert s.supply["Blacksmith"] == 4
    assert sum(c.name == "Town Crier" for c in p.all_cards()) == (1 if rotate else 2)
    assert not any(c.name == "Blacksmith" for c in p.all_cards())
    if effect == "Mirror":
        assert s.mirror_pending[id(p)] == 0
    else:
        assert bool(p.tavern_mat) is rotate


@pytest.mark.parametrize("effect", ["Mirror", "Duplicate"])
@pytest.mark.parametrize("top", ["Sir Martin", "Dame Josephine"])
def test_copy_gain_uses_named_card_at_top_of_knights_pile(effect, top):
    s, p, _ = state()
    s.supply = {"Knights": 2}
    s.pile_order = {"Knights": ["Sir Martin", top]}
    enable_copy(s, p, effect)
    s.gain_card(p, get_card("Sir Martin"), from_supply=False)
    copies = 2 if top == "Sir Martin" else 1
    assert sum(c.name == "Sir Martin" for c in p.all_cards()) == copies
    assert s.supply["Knights"] == (1 if copies == 2 else 2)
    assert s.pile_order["Knights"] == (["Sir Martin"] if copies == 2 else ["Sir Martin", top])


@pytest.mark.parametrize("effect", ["Mirror", "Duplicate"])
def test_copy_gain_cannot_take_non_supply_horse(effect):
    s, p, _ = state()
    s.supply = {"Horse": 10}
    s.non_supply_pile_names = {"Horse"}
    enable_copy(s, p, effect)
    s.gain_card(p, get_card("Horse"), from_supply=False)
    assert sum(c.name == "Horse" for c in p.all_cards()) == 1
    assert s.supply["Horse"] == 10
