"""Tests covering supply counts for core victory piles."""

from dominion.cards.empires.castles import (
    CASTLE_PILE_ORDER,
    HumbleCastle,
    KingsCastle,
)
from dominion.cards.prosperity.colony import Colony
from dominion.cards.victory import Province
from dominion.game.game_state import GameState


def make_state(player_count: int) -> GameState:
    """Create a simple ``GameState`` stub with the requested player count."""

    return GameState(players=[None] * player_count)


def test_province_starting_supply_scales_with_players():
    province = Province()

    assert province.starting_supply(make_state(2)) == 8
    assert province.starting_supply(make_state(3)) == 12
    assert province.starting_supply(make_state(4)) == 12
    assert province.starting_supply(make_state(5)) == 15
    assert province.starting_supply(make_state(6)) == 18


def test_colony_starting_supply_matches_province_rules():
    colony = Colony()

    assert colony.starting_supply(make_state(2)) == 8
    assert colony.starting_supply(make_state(3)) == 12
    assert colony.starting_supply(make_state(4)) == 12
    assert colony.starting_supply(make_state(5)) == 15
    assert colony.starting_supply(make_state(6)) == 18


def test_castle_pile_has_fixed_count():
    """Each Castle pile holds 1 in 2-player and 2 in 3+ player games.

    With eight different Castles, the pile totals 8 cards in 2-player and
    16 cards in 3+ player games.
    """

    humble = HumbleCastle()
    kings = KingsCastle()

    assert humble.starting_supply(make_state(2)) == 1
    assert humble.starting_supply(make_state(4)) == 2
    assert kings.starting_supply(make_state(2)) == 1
    assert kings.starting_supply(make_state(4)) == 2

    assert len(CASTLE_PILE_ORDER) == 8


def test_setup_supply_uses_victory_scaling():
    state = make_state(5)
    state.setup_supply([])

    assert state.supply["Province"] == 15

    state_with_colonies = make_state(6)
    state_with_colonies.setup_supply([Colony()])

    assert state_with_colonies.supply["Province"] == 18
    assert state_with_colonies.supply["Colony"] == 18
