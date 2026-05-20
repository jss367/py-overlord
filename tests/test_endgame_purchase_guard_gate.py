"""The cheap pre-check that gates expensive clone simulation."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _state(supply):
    player = PlayerState(DummyAI())
    state = GameState([player])
    state.log_callback = lambda *_: None
    state.supply = dict(supply)
    return state, player


def test_gate_false_when_game_is_nowhere_near_ending():
    state, player = _state({"Province": 8, "Copper": 30})
    assert state._buy_could_end_game(player, get_card("Province")) is False


def test_gate_true_when_province_pile_is_low():
    state, player = _state({"Province": 2, "Copper": 30})
    assert state._buy_could_end_game(player, get_card("Province")) is True


def test_gate_true_when_colony_pile_is_low():
    state, player = _state({"Province": 8, "Colony": 2, "Copper": 30})
    assert state._buy_could_end_game(player, get_card("Copper")) is True


def test_gate_false_when_colony_not_in_supply():
    state, player = _state({"Province": 8, "Copper": 30})
    assert state._buy_could_end_game(player, get_card("Copper")) is False


def test_gate_true_when_two_piles_already_empty():
    state, player = _state({"Province": 8, "Copper": 30, "Village": 0, "Smithy": 0})
    assert state._buy_could_end_game(player, get_card("Copper")) is True

