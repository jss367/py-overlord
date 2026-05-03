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


class TestTrainHandlesNegativeShapedFitness:
    """train() must still return a strategy when shaping makes every candidate
    score below zero — initializing best_fitness to 0.0 would silently drop
    them all and return None."""

    def test_returns_best_strategy_when_all_fitness_negative(self, monkeypatch):
        trainer = GeneticTrainer(
            ["Village"],
            population_size=4,
            generations=1,
            games_per_eval=2,
            immigrant_fraction=0.0,
            shape_rewards=True,
        )

        scores = iter([-10.0, -5.0, -20.0, -8.0])
        breakdowns = iter([
            [("Opp", 0.0, -50.0, -10.0)],
            [("Opp", 0.0, -25.0, -5.0)],
            [("Opp", 0.0, -100.0, -20.0)],
            [("Opp", 0.0, -40.0, -8.0)],
        ])

        def fake_eval(_strategy):
            trainer.last_eval_breakdown = next(breakdowns)
            return next(scores)

        monkeypatch.setattr(trainer, "evaluate_strategy", fake_eval)

        best, metrics = trainer.train()

        assert best is not None, "train() must not return None when all fitness < 0"
        assert metrics["fitness"] == pytest.approx(-5.0), (
            f"Expected best (least-negative) fitness of -5.0, got {metrics.get('fitness')}"
        )


class TestTrainMetricsDistinguishWinRateFromShapedFitness:
    """With shaping on, metrics['win_rate'] must be the raw win rate, not the
    shaped fitness — otherwise downstream code prints '86% win rate' for a
    100%-winning strategy."""

    def test_metrics_reports_raw_win_rate_alongside_shaped_fitness(self, monkeypatch):
        trainer = GeneticTrainer(
            ["Village"],
            population_size=2,
            generations=1,
            games_per_eval=2,
            immigrant_fraction=0.0,
            shape_rewards=True,
        )

        # First evaluation: shaped fitness 86 backed by a true 100% win rate.
        # Second evaluation: shaped fitness 70 backed by a 50% win rate.
        results = iter([86.0, 70.0])
        breakdowns = iter([
            [("Opp", 100.0, 30.0, 86.0)],
            [("Opp", 50.0, 100.0, 70.0)],
        ])

        def fake_eval(_strategy):
            trainer.last_eval_breakdown = next(breakdowns)
            return next(results)

        monkeypatch.setattr(trainer, "evaluate_strategy", fake_eval)

        _, metrics = trainer.train()

        assert metrics["fitness"] == pytest.approx(86.0)
        assert metrics["win_rate"] == pytest.approx(100.0), (
            f"win_rate should be the raw 100% mean, got {metrics['win_rate']}"
        )

    def test_failed_eval_does_not_outrank_negative_shaped_fitness(self, monkeypatch):
        """If evaluate_strategy hits its exception path it must NOT become the
        global best when valid candidates have negative shaped fitness."""
        trainer = GeneticTrainer(
            ["Village"],
            population_size=2,
            generations=1,
            games_per_eval=2,
            immigrant_fraction=0.0,
            simplify_genomes=False,
            shape_rewards=True,
        )

        # Force evaluate_strategy down its exception path. It should clear
        # the breakdown and return a sentinel that loses to any real fitness.
        def boom(_strategy):
            raise RuntimeError("simulated game failure")

        monkeypatch.setattr(trainer.battle_system, "run_game", boom)

        # First strategy: failed eval. Second: valid negative shaped fitness.
        eval_results = []

        original_eval = trainer.evaluate_strategy
        call_count = {"n": 0}

        def patched_eval(strategy):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Real exception path
                fitness = original_eval(strategy)
            else:
                # Valid negative shaped fitness; populate breakdown directly
                trainer.last_eval_breakdown = [("Opp", 0.0, -50.0, -10.0)]
                fitness = -10.0
            eval_results.append(fitness)
            return fitness

        monkeypatch.setattr(trainer, "evaluate_strategy", patched_eval)

        best, metrics = trainer.train()

        assert eval_results[0] < eval_results[1], (
            f"Failed eval ({eval_results[0]}) must lose to a valid negative fitness "
            f"({eval_results[1]}); otherwise failures look 'best'"
        )
        assert metrics["fitness"] == pytest.approx(-10.0)

    def test_failed_eval_clears_breakdown(self, monkeypatch):
        """A failed evaluation must reset last_eval_breakdown so a later
        consumer can't read stale data from the prior strategy."""
        trainer = GeneticTrainer(
            ["Village"],
            population_size=1,
            generations=1,
            games_per_eval=2,
            shape_rewards=True,
        )
        # Pre-populate breakdown to simulate "previous successful eval".
        trainer.last_eval_breakdown = [("Opp", 100.0, 30.0, 86.0)]

        def boom(*_args, **_kwargs):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(trainer.battle_system, "run_game", boom)

        strategy = _make_stub_strategy()
        opp = _make_dummy_opponent("Opp")
        trainer.set_baseline_panel([opp])
        trainer.evaluate_strategy(strategy)

        assert trainer.last_eval_breakdown == [], (
            f"Expected breakdown cleared after failed eval, got {trainer.last_eval_breakdown}"
        )

    def test_metrics_winrate_equals_fitness_when_shaping_off(self, monkeypatch):
        """With shaping off, fitness *is* the mean win rate; the two metrics
        keys should be equal so we don't break the historical contract."""
        trainer = GeneticTrainer(
            ["Village"],
            population_size=1,
            generations=1,
            games_per_eval=2,
            immigrant_fraction=0.0,
            shape_rewards=False,
        )

        def fake_eval(_strategy):
            trainer.last_eval_breakdown = [("Opp", 75.0)]
            return 75.0

        monkeypatch.setattr(trainer, "evaluate_strategy", fake_eval)

        _, metrics = trainer.train()

        assert metrics["win_rate"] == pytest.approx(75.0)
        assert metrics["fitness"] == pytest.approx(75.0)
