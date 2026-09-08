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
