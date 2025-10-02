from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


def make_state_with_taskmaster():
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    state.log_callback = lambda *args, **kwargs: None
    taskmaster = get_card("Taskmaster")
    taskmaster.play_effect(state)
    # Sanity check to ensure setup matches gameplay expectations
    assert player.duration == [taskmaster]
    return state, player, taskmaster


def test_taskmaster_leaves_without_five_cost_gain():
    state, player, taskmaster = make_state_with_taskmaster()
    player.actions = 0
    player.coins = 0
    player.gained_five_last_turn = False

    state.do_duration_phase()

    assert player.actions == 0
    assert player.coins == 0
    assert taskmaster not in player.duration
    assert taskmaster in player.discard


def test_taskmaster_persists_across_consecutive_five_cost_gains():
    state, player, taskmaster = make_state_with_taskmaster()
    player.actions = 0
    player.coins = 0

    player.gained_five_last_turn = True
    state.do_duration_phase()

    assert player.actions == 1
    assert player.coins == 1
    assert player.duration == [taskmaster]
    assert taskmaster.duration_persistent is True
    assert taskmaster not in player.discard

    player.gained_five_last_turn = True
    state.do_duration_phase()

    assert player.actions == 2
    assert player.coins == 2
    assert player.duration == [taskmaster]
    assert taskmaster.duration_persistent is True
    assert player.discard == []

    player.gained_five_last_turn = False
    state.do_duration_phase()

    assert player.actions == 2
    assert player.coins == 2
    assert taskmaster not in player.duration
    assert player.discard == [taskmaster]
