"""The correctness boundary for AIs with non-pure decision hooks."""

from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def test_purity_default_true_for_baseline_ai():
    state = GameState([PlayerState(DummyAI()), PlayerState(DummyAI())])
    assert state._all_decision_hooks_pure() is True


def test_purity_false_when_any_ai_opts_out():
    p1 = PlayerState(DummyAI())
    p2 = PlayerState(DummyAI())
    p2.ai.decision_hooks_are_pure = False
    state = GameState([p1, p2])
    assert state._all_decision_hooks_pure() is False


def test_rl_ai_class_marks_itself_impure():
    from dominion.rl.rl_ai import RLAI

    assert getattr(RLAI, "decision_hooks_are_pure", True) is False

