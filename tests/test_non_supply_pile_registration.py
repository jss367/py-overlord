"""Regression tests for Dark Ages non-Supply pile registration.

Madman (from Hermit), Mercenary (from Urchin), and Spoils (from
Marauder / Bandit Camp / Pillage) were historically added directly to
``state.supply`` during game setup without being marked in
``state.non_supply_pile_names``. That meant if all 10 Madman or all 15
Spoils were gained, the pile would count toward the three-empty-piles
game-end condition — wrong, since per the official rules these are
non-Supply piles and never count.

These tests pin the corrected behaviour: each of those piles is
registered in ``non_supply_pile_names`` and depleting them does not
advance ``empty_piles``.
"""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState

from tests.utils import DummyAI


def _initialize_with(kingdom_names):
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.initialize_game(
        [DummyAI()], [get_card(n) for n in kingdom_names]
    )
    return state


def test_madman_is_a_non_supply_pile():
    state = _initialize_with(["Hermit"])
    assert "Madman" in state.supply, "Madman pile must exist for lookup/gain"
    assert "Madman" in state.non_supply_pile_names, (
        "Madman must be flagged non-Supply so it does not count toward "
        "the three-empty-piles game end"
    )


def test_mercenary_is_a_non_supply_pile():
    state = _initialize_with(["Urchin"])
    assert "Mercenary" in state.supply
    assert "Mercenary" in state.non_supply_pile_names


def test_spoils_is_a_non_supply_pile_via_marauder():
    state = _initialize_with(["Marauder"])
    assert "Spoils" in state.supply
    assert "Spoils" in state.non_supply_pile_names


def test_spoils_is_a_non_supply_pile_via_bandit_camp():
    state = _initialize_with(["Bandit Camp"])
    assert "Spoils" in state.supply
    assert "Spoils" in state.non_supply_pile_names


def test_spoils_is_a_non_supply_pile_via_pillage():
    state = _initialize_with(["Pillage"])
    assert "Spoils" in state.supply
    assert "Spoils" in state.non_supply_pile_names


def test_emptied_dark_ages_non_supply_piles_do_not_advance_empty_count():
    """Three depleted Dark Ages non-Supply piles must NOT advance the
    three-empty-piles end-game counter on their own."""
    state = _initialize_with(["Hermit", "Urchin", "Marauder"])
    assert state.empty_piles == 0
    for name in ("Madman", "Mercenary", "Spoils"):
        assert name in state.supply
        state.supply[name] = 0
    assert state.empty_piles == 0
