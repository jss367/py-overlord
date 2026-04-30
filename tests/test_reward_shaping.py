"""Tests for reward shaping in the genetic trainer.

Reward shaping mixes win rate with average score margin to give the trainer
a smoother fitness gradient. When ``shape_rewards=False``, fitness must
remain exactly the per-opponent win-rate mean (existing behavior preserved).
"""

from __future__ import annotations

import types

import pytest

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


def _make_stub_strategy(name: str = "Stub") -> BaseStrategy:
    s = BaseStrategy()
    s.name = name
    s.gain_priority = [PriorityRule("Province")]
    s.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]
    return s


def _make_dummy_opponent(name: str) -> BaseStrategy:
    opp = BaseStrategy()
    opp.name = name
    opp.gain_priority = [PriorityRule("Province")]
    opp.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]
    return opp


def _patch_run_game(trainer, monkeypatch, *, my_score, opp_score, my_wins):
    """Patch run_game on the trainer's battle_system to return deterministic
    scores. The "Stub" strategy is treated as ours."""

    def fake_run_game(first_ai, second_ai, kingdom):
        if first_ai.strategy.name == "Stub":
            mine, other = first_ai, second_ai
        else:
            mine, other = second_ai, first_ai
        scores = {mine.name: my_score, other.name: opp_score}
        winner = mine if my_wins else other
        return winner, scores, None, 0

    monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)


# ---------------------------------------------------------------------------
# Direct tests of the margin-mapping helper
# ---------------------------------------------------------------------------


class TestMarginScoreFormula:
    """Map an average VP margin to a [-100, 100] contribution. The spec maps
    +20 avg margin to +20 fitness points and -20 avg margin to -20, so the
    scale is identity (with clipping to [-100, 100])."""

    def test_zero_margin_is_zero(self):
        assert GeneticTrainer._margin_to_score(0.0) == 0.0

    def test_positive_twenty_margin_is_twenty(self):
        assert GeneticTrainer._margin_to_score(20.0) == pytest.approx(20.0)

    def test_negative_twenty_margin_is_minus_twenty(self):
        assert GeneticTrainer._margin_to_score(-20.0) == pytest.approx(-20.0)

    def test_small_positive_margin_scales_linearly(self):
        assert GeneticTrainer._margin_to_score(5.0) == pytest.approx(5.0)

    def test_huge_positive_margin_clamps_at_100(self):
        assert GeneticTrainer._margin_to_score(500.0) == 100.0

    def test_huge_negative_margin_clamps_at_minus_100(self):
        assert GeneticTrainer._margin_to_score(-500.0) == -100.0


# ---------------------------------------------------------------------------
# evaluate_strategy: shaping flag behavior
# ---------------------------------------------------------------------------


class TestShapeRewardsOff:
    """With ``shape_rewards=False`` the trainer must produce the exact same
    fitness it always has - pure win-rate average across the panel."""

    def test_default_behavior_unchanged_when_off(self, monkeypatch):
        trainer = GeneticTrainer(
            ["Village"],
            population_size=1,
            generations=1,
            games_per_eval=4,
            shape_rewards=False,
        )
        strategy = _make_stub_strategy()
        opp = _make_dummy_opponent("Opp")
        trainer.set_baseline_panel([opp])

        # Stub wins every game by 30 VP. With shaping off, fitness must be
        # exactly the win rate (100.0), regardless of margin.
        _patch_run_game(trainer, monkeypatch, my_score=40, opp_score=10, my_wins=True)

        fitness = trainer.evaluate_strategy(strategy)
        assert fitness == 100.0

    def test_breakdown_entries_remain_compatible_when_off(self, monkeypatch):
        trainer = GeneticTrainer(
            ["Village"],
            population_size=1,
            generations=1,
            games_per_eval=2,
            shape_rewards=False,
        )
        strategy = _make_stub_strategy()
        opp = _make_dummy_opponent("Opp")
        trainer.set_baseline_panel([opp])

        _patch_run_game(trainer, monkeypatch, my_score=20, opp_score=10, my_wins=True)
        trainer.evaluate_strategy(strategy)
        for entry in trainer.last_eval_breakdown:
            # First two fields are the stable (name, win_rate) contract.
            assert isinstance(entry[0], str)
            assert isinstance(entry[1], float)


class TestShapeRewardsOn:
    """When shaping is on, fitness should be 0.8 * win_rate + 0.2 * margin_score."""

    def test_shaped_fitness_with_full_winrate_and_positive_margin(self, monkeypatch):
        trainer = GeneticTrainer(
            ["Village"],
            population_size=1,
            generations=1,
            games_per_eval=4,
            shape_rewards=True,
        )
        strategy = _make_stub_strategy()
        opp = _make_dummy_opponent("Opp")
        trainer.set_baseline_panel([opp])

        # Win every game by 30 VP. 100% win rate -> 0.8*100 = 80.
        # Avg margin 30 -> margin_score 30 -> 0.2*30 = 6. Total 86.
        _patch_run_game(trainer, monkeypatch, my_score=40, opp_score=10, my_wins=True)
        fitness = trainer.evaluate_strategy(strategy)
        assert fitness == pytest.approx(86.0)

    def test_constant_winrate_higher_margin_yields_higher_fitness(self, monkeypatch):
        """At equal win rate, larger positive margins give higher fitness."""

        def run_one(my_score, opp_score):
            trainer = GeneticTrainer(
                ["Village"],
                population_size=1,
                generations=1,
                games_per_eval=4,
                shape_rewards=True,
            )
            strategy = _make_stub_strategy()
            opp = _make_dummy_opponent("Opp")
            trainer.set_baseline_panel([opp])

            calls = types.SimpleNamespace(n=0)

            def fake_run_game(first_ai, second_ai, kingdom):
                calls.n += 1
                if first_ai.strategy.name == "Stub":
                    mine, other = first_ai, second_ai
                else:
                    mine, other = second_ai, first_ai
                # Alternate winners -> 50% win rate
                winner = mine if calls.n % 2 == 1 else other
                scores = {mine.name: my_score, other.name: opp_score}
                return winner, scores, None, 0

            monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)
            return trainer.evaluate_strategy(strategy)

        low = run_one(15, 10)   # +5 avg margin
        high = run_one(40, 10)  # +30 avg margin
        assert high > low, f"High margin fitness ({high}) should beat low ({low})"

    def test_negative_margin_drives_fitness_below_zero(self, monkeypatch):
        """0% win rate plus a -40 avg margin: 0.8*0 + 0.2*(-40) = -8."""
        trainer = GeneticTrainer(
            ["Village"],
            population_size=1,
            generations=1,
            games_per_eval=2,
            shape_rewards=True,
        )
        strategy = _make_stub_strategy()
        opp = _make_dummy_opponent("Opp")
        trainer.set_baseline_panel([opp])

        _patch_run_game(trainer, monkeypatch, my_score=5, opp_score=45, my_wins=False)
        fitness = trainer.evaluate_strategy(strategy)
        assert fitness == pytest.approx(-8.0)

    def test_breakdown_includes_margin_when_on(self, monkeypatch):
        trainer = GeneticTrainer(
            ["Village"],
            population_size=1,
            generations=1,
            games_per_eval=2,
            shape_rewards=True,
        )
        strategy = _make_stub_strategy()
        opp = _make_dummy_opponent("Opp")
        trainer.set_baseline_panel([opp])

        _patch_run_game(trainer, monkeypatch, my_score=30, opp_score=10, my_wins=True)
        trainer.evaluate_strategy(strategy)

        assert trainer.last_eval_breakdown
        entry = trainer.last_eval_breakdown[0]
        assert len(entry) >= 3, f"Expected (name, rate, margin) tuple, got {entry}"
        name, rate, margin = entry[0], entry[1], entry[2]
        assert name == "Opp"
        assert rate == 100.0
        assert margin == pytest.approx(20.0)


class TestShapeRewardsDefaultsOn:
    """The constructor flag defaults to True per the PR plan."""

    def test_default_is_shaping_enabled(self):
        trainer = GeneticTrainer(["Village"], population_size=1, generations=1)
        assert trainer.shape_rewards is True
