"""Tests for PriorityRule predicate helpers introduced for Cauldron-style triggers.

These exercise the per-turn gain counters (``actions_gained_this_turn`` and
``cards_gained_this_turn``) that ``PlayerState`` tracks, and verify that the
helpers tag the resulting callables with a ``_source`` string so they round-trip
through the strategy serializer.
"""

import types

from dominion.strategy.enhanced_strategy import PriorityRule


def _make_mock_state():
    state = types.SimpleNamespace()
    state.turn_number = 1
    state.supply = {}
    state.empty_piles = 0
    state.players = []
    return state


def _make_mock_player(actions_gained_this_turn=0, cards_gained_this_turn=0):
    player = types.SimpleNamespace()
    player.actions_gained_this_turn = actions_gained_this_turn
    player.cards_gained_this_turn = cards_gained_this_turn
    player.in_play = []
    player.hand = []
    return player


class TestActionsGainedThisTurn:
    def test_evaluates_true_when_threshold_met(self):
        cond = PriorityRule.actions_gained_this_turn(">=", 2)
        assert cond(_make_mock_state(), _make_mock_player(actions_gained_this_turn=3)) is True

    def test_evaluates_false_when_threshold_not_met(self):
        cond = PriorityRule.actions_gained_this_turn(">=", 3)
        assert cond(_make_mock_state(), _make_mock_player(actions_gained_this_turn=2)) is False

    def test_supports_lt(self):
        cond = PriorityRule.actions_gained_this_turn("<", 2)
        assert cond(_make_mock_state(), _make_mock_player(actions_gained_this_turn=1)) is True
        assert cond(_make_mock_state(), _make_mock_player(actions_gained_this_turn=2)) is False

    def test_supports_le(self):
        cond = PriorityRule.actions_gained_this_turn("<=", 2)
        assert cond(_make_mock_state(), _make_mock_player(actions_gained_this_turn=2)) is True
        assert cond(_make_mock_state(), _make_mock_player(actions_gained_this_turn=3)) is False

    def test_supports_gt(self):
        cond = PriorityRule.actions_gained_this_turn(">", 0)
        assert cond(_make_mock_state(), _make_mock_player(actions_gained_this_turn=1)) is True
        assert cond(_make_mock_state(), _make_mock_player(actions_gained_this_turn=0)) is False

    def test_source_tagged(self):
        cond = PriorityRule.actions_gained_this_turn(">=", 2)
        assert cond._source == "PriorityRule.actions_gained_this_turn('>=', 2)"


class TestCardsGainedThisTurn:
    def test_evaluates_true_when_threshold_met(self):
        cond = PriorityRule.cards_gained_this_turn(">=", 3)
        assert cond(_make_mock_state(), _make_mock_player(cards_gained_this_turn=4)) is True

    def test_evaluates_false_when_threshold_not_met(self):
        cond = PriorityRule.cards_gained_this_turn(">=", 5)
        assert cond(_make_mock_state(), _make_mock_player(cards_gained_this_turn=2)) is False

    def test_supports_lt(self):
        cond = PriorityRule.cards_gained_this_turn("<", 3)
        assert cond(_make_mock_state(), _make_mock_player(cards_gained_this_turn=2)) is True
        assert cond(_make_mock_state(), _make_mock_player(cards_gained_this_turn=3)) is False

    def test_source_tagged(self):
        cond = PriorityRule.cards_gained_this_turn("<=", 4)
        assert cond._source == "PriorityRule.cards_gained_this_turn('<=', 4)"
