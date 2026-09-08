"""Gain triggers must already exist when the gain happens."""

import pytest

from dominion.cards.registry import get_card
from dominion.projects.innovation import Innovation
from dominion.traits import apply_trait
from tests.test_allies_printed_rules import cards, state


@pytest.mark.parametrize("name", ["Skirmisher", "Guildmaster", "Galleria"])
@pytest.mark.parametrize("method", ["Innovation", "Hasty City-state"])
def test_playing_a_gain_registers_effects_only_for_subsequent_gains(name, method):
    s, p, q = state("City-state" if method == "Hasty City-state" else None)
    s.setup_supply([get_card(n) for n in {name, "Skirmisher"}])
    p.favors = 2 if method == "Hasty City-state" else 0
    p.deck = cards("Copper", 10)
    q.hand = cards("Copper", 5)
    if name == "Galleria":
        p.cost_reduction = 2  # Its own gain and the next Attack cost $3.
    if method == "Innovation":
        p.projects = [Innovation()]
    else:
        apply_trait(s, "Hasty", name)
    gained = s.take_top_supply_card(name)
    s.gain_card(p, gained)
    assert gained in p.in_play
    assert p.favors == 0
    assert p.buys == 1
    assert len(q.hand) == 5

    attack = s.take_top_supply_card("Skirmisher")
    s.gain_card(p, attack)
    assert p.favors == (1 if name == "Guildmaster" else 0)
    assert p.buys == (2 if name == "Galleria" else 1)
    assert len(q.hand) == (3 if name == "Skirmisher" else 5)


def test_new_gain_effect_applies_to_nested_gains_but_not_the_outer_gain():
    s, p, _ = state()
    s.setup_supply([get_card("Guildmaster")])
    apply_trait(s, "Rich", "Guildmaster")
    p.projects = [Innovation()]
    guildmaster = s.take_top_supply_card("Guildmaster")
    s.gain_card(p, guildmaster)
    assert guildmaster in p.in_play
    assert [c.name for c in p.discard] == ["Silver"]
    assert p.favors == 1  # Only Rich's nested Silver gain earns a Favor.


@pytest.mark.parametrize("method", ["Innovation", "City-state"])
@pytest.mark.parametrize("reduction", [0, 1, 2])
def test_galleria_uses_cost_before_gained_highway_is_played(method, reduction):
    from tests.test_allies_interactions import ChoiceAI
    from tests.test_allies_printed_rules import play

    s, p, _ = state("City-state" if method == "City-state" else None)
    s.setup_supply([get_card("Highway")])
    p.ai = ChoiceAI({"city_state_before_gain_effects": True})
    p.favors = 2
    p.deck = cards("Copper", 5)
    if method == "Innovation":
        p.projects = [Innovation()]
    play(s, p, "Galleria")
    p.cost_reduction = reduction
    before = p.buys
    highway = s.take_top_supply_card("Highway")
    s.gain_card(p, highway)
    assert highway in p.in_play
    assert s.get_card_cost(p, highway) == 4 - reduction
    assert p.buys == before + int(reduction > 0)
    # A subsequent gain uses the new cost, without changing the outer trigger.
    s.gain_card(p, s.take_top_supply_card("Silver"))
    assert p.buys == before + int(reduction > 0)
