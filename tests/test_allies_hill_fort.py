"""Hill Fort's default mode accounts for completed gain reactions."""

import pytest

from dominion.cards.registry import get_card
from dominion.traits import apply_trait
from tests.test_allies_interactions import ChoiceAI
from tests.test_allies_printed_rules import cards, play, state


@pytest.mark.parametrize("mover", [None, "trash", "topdeck", "Hasty", "City-state"])
def test_hill_fort_defaults_to_cycle_after_gain_moves(mover):
    class AI(ChoiceAI):
        def choose_watchtower_reaction(self, state, player, card):
            return mover

    s, p, _ = state("City-state" if mover == "City-state" else None)
    p.ai = AI()
    p.favors = 2
    p.deck = cards("Copper", 5)
    s.supply = {"Village": 1}
    if mover in {"trash", "topdeck"}:
        p.hand = [get_card("Watchtower")]
    elif mover == "Hasty":
        apply_trait(s, "Hasty", "Village")
    actions_before = p.actions
    hand_before = len(p.hand)
    play(s, p, "Hill Fort")
    assert p.actions == actions_before + (3 if mover == "City-state" else int(mover is not None))
    assert len(p.hand) == hand_before + (2 if mover == "City-state" else 1)
    if mover in {None, "topdeck"}:
        assert p.hand[-1].name == "Village"
    else:
        assert p.hand[-1].name == "Copper"
    if mover == "trash":
        assert [c.name for c in s.trash] == ["Village"]
    elif mover == "Hasty":
        assert [c.name for c in s.hasty_set_aside[id(p)]] == ["Village"]
    elif mover == "City-state":
        assert [c.name for c in p.in_play] == ["Hill Fort", "Village"]
