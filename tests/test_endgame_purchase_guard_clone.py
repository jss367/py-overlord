"""Clone semantics required by the real-buy-simulation endgame guard."""

import copy

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _make_two_player_state():
    p1 = PlayerState(DummyAI())
    p2 = PlayerState(DummyAI())
    state = GameState([p1, p2])
    state.log_callback = lambda *_: None
    state.supply = {"Province": 8, "Copper": 30}
    return state


def test_deepcopy_shares_ai_by_reference():
    state = _make_two_player_state()
    clone = copy.deepcopy(state)
    for original, copied in zip(state.players, clone.players):
        assert copied.ai is original.ai


def test_deepcopy_detaches_logger_and_log_callback():
    state = _make_two_player_state()
    clone = copy.deepcopy(state)
    assert clone.logger is None
    clone.log_callback("anything", "at", "all")


def test_deepcopy_fixes_player_game_state_backref():
    state = _make_two_player_state()
    for player in state.players:
        player.game_state = state
    clone = copy.deepcopy(state)
    for cloned_player in clone.players:
        assert cloned_player.game_state is clone


def test_deepcopy_supply_is_independent():
    state = _make_two_player_state()
    clone = copy.deepcopy(state)
    clone.supply["Province"] = 0
    assert state.supply["Province"] == 8


def test_deepcopy_player_zones_are_independent():
    state = _make_two_player_state()
    state.players[0].discard.append(get_card("Estate"))
    clone = copy.deepcopy(state)
    clone.players[0].discard.append(get_card("Duchy"))
    assert [card.name for card in state.players[0].discard] == ["Estate"]

