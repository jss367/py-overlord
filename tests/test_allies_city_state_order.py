"""City-state can precede simultaneous gain movers without duplicating a card."""

import pytest

from dominion.cards.registry import get_card
from dominion.projects.innovation import Innovation
from dominion.traits import apply_trait
from tests.test_allies_interactions import ChoiceAI
from tests.test_allies_printed_rules import cards, play, state


@pytest.mark.parametrize("mover", [
    "Watchtower topdeck", "Watchtower trash", "Royal Seal", "Sleigh hand",
    "Sleigh deck", "Cargo Ship", "Gatekeeper", "Innovation", "Hasty", "Deliver",
])
@pytest.mark.parametrize("city_first", [False, True])
def test_city_state_can_resolve_before_or_after_gain_movers(mover, city_first):
    class AI(ChoiceAI):
        def choose_watchtower_reaction(self, state, player, card):
            return "trash" if mover.endswith("trash") else "topdeck"

        def should_topdeck_with_royal_seal(self, state, player, card):
            return True

        def choose_sleigh_reaction(self, state, player, card):
            return "hand" if mover.endswith("hand") else "deck"

        def should_set_aside_cargo_ship(self, state, player, card):
            return True

    s, p, _ = state("City-state")
    s.setup_supply([get_card("Village")])
    p.ai = AI({"city_state_before_gain_effects": city_first})
    p.favors = 2
    p.deck = cards("Copper", 5)
    if mover.startswith("Watchtower"):
        p.hand = [get_card("Watchtower")]
    elif mover.startswith("Sleigh"):
        p.hand = [get_card("Sleigh")]
    elif mover == "Royal Seal":
        p.in_play = [get_card("Royal Seal")]
    elif mover == "Cargo Ship":
        cargo = play(s, p, "Cargo Ship")
    elif mover == "Gatekeeper":
        p.gatekeeper_attacks = 1
    elif mover == "Innovation":
        p.projects = [Innovation()]
    elif mover == "Hasty":
        apply_trait(s, "Hasty", "Village")
    else:
        p.deliver_pending_count = 1
    village = s.take_top_supply_card("Village")
    actions_before = p.actions
    s.gain_card(p, village)
    played = city_first or mover == "Innovation"
    assert p.favors == (0 if city_first else 2)
    assert p.in_play.count(village) == int(played)
    assert p.actions == actions_before + (2 if played else 0)
    assert sum(c.name == "Copper" for c in p.hand) == int(played)
    if city_first:
        assert village not in p.hand + p.deck + p.discard + p.exile + s.trash
        assert village not in s.hasty_set_aside.get(id(p), []) + p.deliver_set_aside
        if mover == "Cargo Ship":
            assert cargo.set_aside is None
    elif mover == "Watchtower trash":
        assert village in s.trash
    elif mover in {"Watchtower topdeck", "Royal Seal", "Sleigh deck"}:
        assert p.deck[-1] is village
    elif mover == "Sleigh hand":
        assert village in p.hand
    elif mover == "Cargo Ship":
        assert cargo.set_aside is village
    elif mover == "Gatekeeper":
        assert village in p.exile
    elif mover == "Hasty":
        assert village in s.hasty_set_aside[id(p)]
    elif mover == "Deliver":
        assert village in p.deliver_set_aside
    if mover == "Innovation":
        assert p.innovation_used
    if mover == "Deliver":
        assert p.deliver_pending_count == 0


def test_city_state_played_livery_does_not_react_to_its_own_gain():
    s, p, _ = state("City-state")
    s.setup_supply([get_card("Livery")])
    p.ai = ChoiceAI({"city_state_before_gain_effects": True})
    p.favors = 2
    livery = s.take_top_supply_card("Livery")
    s.gain_card(p, livery)
    assert livery in p.in_play
    assert p.discard == []
    s.gain_card(p, s.take_top_supply_card("Gold"))
    assert [c.name for c in p.discard] == ["Gold", "Horse"]


def test_city_state_played_cargo_ship_only_sets_aside_a_subsequent_gain():
    s, p, _ = state("City-state")
    s.setup_supply([get_card("Cargo Ship")])
    p.ai = ChoiceAI({"city_state_before_gain_effects": True})
    p.ai.should_set_aside_cargo_ship = lambda *args: True
    p.favors = 2
    cargo = s.take_top_supply_card("Cargo Ship")
    s.gain_card(p, cargo)
    assert cargo in p.in_play
    assert cargo.set_aside is None
    assert cargo.waiting_for_gain
    gold = s.take_top_supply_card("Gold")
    s.gain_card(p, gold)
    assert cargo.set_aside is gold
    assert gold not in p.hand + p.deck + p.discard
