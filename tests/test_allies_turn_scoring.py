"""Skipped turns and pending gains retain their scoring semantics."""

from copy import deepcopy

import pytest

from dominion.cards.registry import get_card
from dominion.simulation.strategy_battle import StrategyBattle
from tests.test_allies_printed_rules import play, state


@pytest.mark.parametrize("skips", [1, 2])
def test_lich_skipped_turns_do_not_change_the_fewer_turns_tiebreak(skips):
    s, p, q = state()
    p.turns_taken, q.turns_taken = 1, 2
    for _ in range(skips):
        play(s, p, "Lich")
    for _ in range(skips):
        s.current_player_index = 0
        s.handle_start_phase()
        assert s.current_player is q
    assert p.turns_to_skip == 0
    assert p.turns_taken == 1
    assert p.get_victory_points() == q.get_victory_points()
    assert StrategyBattle._select_winner([q, p]) is p


@pytest.mark.parametrize("copied", [False, True])
def test_deliver_set_aside_victory_card_remains_owned_and_scored(copied):
    s, p, _ = state()
    s.setup_supply([])
    p.deliver_pending_count = 1
    province = s.take_top_supply_card("Province")
    s.gain_card(p, province)
    if copied:
        s = deepcopy(s)
        p = s.players[0]
    assert [c.name for c in p.deliver_set_aside] == ["Province"]
    assert [c.name for c in p.all_cards()] == ["Province"]
    assert p.get_victory_points() == 6
