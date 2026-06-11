"""Tests for the evaluation-integrity overhaul.

Covers the three mechanisms added to make fitness trustworthy:

1. Common random numbers — seeded, seat-swapped game pairs so every candidate
   in an evaluation phase plays identical shuffles.
2. Racing — cheap screening for all, refinement for the top slice, and
   champion replacement only after a paired confirmation eval (closes the
   winner's-curse path where the returned champion was the luckiest single
   eval out of thousands).
3. Hall of fame — past champions join the opponent panel so the fitness
   gradient doesn't saturate once the population beats the static baselines.

Plus the official-rules tie-break in StrategyBattle (fewer turns wins ties).
"""

from __future__ import annotations

import random
import types

import pytest

from dominion.simulation.genetic_trainer import (
    _SEED_PHASE_CONFIRM,
    _SEED_PHASE_SCREEN,
    GeneticTrainer,
)
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


def _make_strategy(name: str, *gain_cards: str) -> BaseStrategy:
    s = BaseStrategy()
    s.name = name
    s.gain_priority = [PriorityRule(c) for c in (gain_cards or ("Province",))]
    s.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]
    return s


def _make_trainer(**kwargs) -> GeneticTrainer:
    defaults = dict(
        kingdom_cards=["Village", "Smithy"],
        population_size=4,
        generations=1,
        games_per_eval=2,
        eval_seed=1234,
    )
    defaults.update(kwargs)
    return GeneticTrainer(**defaults)


# ---------------------------------------------------------------------------
# Tie-break: fewer turns wins on equal VP
# ---------------------------------------------------------------------------


class TestSelectWinner:
    @staticmethod
    def _player(vp: int, turns: int):
        return types.SimpleNamespace(
            get_victory_points=lambda _vp=vp: _vp,
            turns_taken=turns,
            ai=object(),
        )

    def test_higher_vp_wins_regardless_of_turns(self):
        a = self._player(vp=20, turns=18)
        b = self._player(vp=15, turns=15)
        assert StrategyBattle._select_winner([a, b]) is a

    def test_equal_vp_fewer_turns_wins(self):
        a = self._player(vp=20, turns=18)
        b = self._player(vp=20, turns=17)
        assert StrategyBattle._select_winner([a, b]) is b

    def test_full_tie_falls_back_to_seat_order(self):
        a = self._player(vp=20, turns=18)
        b = self._player(vp=20, turns=18)
        assert StrategyBattle._select_winner([a, b]) is a


# ---------------------------------------------------------------------------
# Common random numbers
# ---------------------------------------------------------------------------


class TestGameSeeds:
    def test_seat_swapped_pairs_share_a_seed(self):
        trainer = _make_trainer()
        trainer._eval_seed_context = (_SEED_PHASE_SCREEN, 0)
        assert trainer._game_seed(0, 0) == trainer._game_seed(0, 1)
        assert trainer._game_seed(0, 2) == trainer._game_seed(0, 3)
        assert trainer._game_seed(0, 0) != trainer._game_seed(0, 2)

    def test_seeds_differ_across_opponents_and_contexts(self):
        trainer = _make_trainer()
        trainer._eval_seed_context = (_SEED_PHASE_SCREEN, 0)
        seed_a = trainer._game_seed(0, 0)
        seed_b = trainer._game_seed(1, 0)
        trainer._eval_seed_context = (_SEED_PHASE_SCREEN, 1)
        seed_c = trainer._game_seed(0, 0)
        assert seed_a != seed_b
        assert seed_a != seed_c

    def test_seeds_do_not_depend_on_candidate(self):
        """The seed is a function of (base, context, opponent, pair) only —
        that's what makes the random numbers common across candidates."""
        t1 = _make_trainer(eval_seed=42)
        t2 = _make_trainer(eval_seed=42)
        t1._eval_seed_context = t2._eval_seed_context = (_SEED_PHASE_CONFIRM, 7)
        assert [t1._game_seed(0, g) for g in range(6)] == [t2._game_seed(0, g) for g in range(6)]


class TestSeededEvaluationDeterminism:
    def test_same_context_same_fitness(self):
        """Two seeded evals of the same strategy in the same context play the
        exact same games and must return identical fitness and breakdown."""
        trainer = _make_trainer(games_per_eval=12)
        strategy = _make_strategy("Det", "Province", "Gold", "Silver")

        trainer._eval_seed_context = (_SEED_PHASE_SCREEN, 0)
        first = trainer.evaluate_strategy(strategy)
        first_breakdown = list(trainer.last_eval_breakdown)
        second = trainer.evaluate_strategy(strategy)
        second_breakdown = list(trainer.last_eval_breakdown)

        assert first == second
        assert first_breakdown == second_breakdown

    def test_seeded_eval_restores_global_rng_state(self):
        """Seeding games must not make the GA's own mutation stream
        deterministic: the global RNG state is restored after the eval."""
        trainer = _make_trainer(games_per_eval=2)
        strategy = _make_strategy("RngGuard", "Province")

        random.seed(987)
        expected_next = random.Random()
        expected_next.seed(987)
        expected_values = [expected_next.random() for _ in range(3)]

        trainer._eval_seed_context = (_SEED_PHASE_SCREEN, 0)
        trainer.evaluate_strategy(strategy)

        assert [random.random() for _ in range(3)] == expected_values

    def test_unseeded_eval_keeps_legacy_stochastic_behavior(self):
        """With no seed context, evals consume global randomness exactly as
        before — two evals must NOT replay the same RNG stream."""
        trainer = _make_trainer(games_per_eval=2)
        strategy = _make_strategy("Legacy", "Province")

        random.seed(555)
        state_before = random.getstate()
        assert trainer._eval_seed_context is None
        trainer.evaluate_strategy(strategy)
        assert random.getstate() != state_before


# ---------------------------------------------------------------------------
# _eval_with_budget
# ---------------------------------------------------------------------------


class TestEvalWithBudget:
    def test_budget_and_context_are_temporary(self, monkeypatch):
        trainer = _make_trainer(games_per_eval=2)
        seen = {}

        def fake(strategy):
            seen["games"] = trainer.games_per_eval
            seen["context"] = trainer._eval_seed_context
            return 42.0

        monkeypatch.setattr(trainer, "evaluate_strategy", fake)
        result = trainer._eval_with_budget(_make_strategy("X"), 16, (_SEED_PHASE_CONFIRM, 3))

        assert result == 42.0
        assert seen["games"] == 16
        assert seen["context"] == (_SEED_PHASE_CONFIRM, 3)
        assert trainer.games_per_eval == 2
        assert trainer._eval_seed_context is None

    def test_crn_disabled_means_no_seed_context(self, monkeypatch):
        trainer = _make_trainer(common_random_numbers=False)
        seen = {}

        def fake(strategy):
            seen["context"] = trainer._eval_seed_context
            return 0.0

        monkeypatch.setattr(trainer, "evaluate_strategy", fake)
        trainer._eval_with_budget(_make_strategy("X"), 8, (_SEED_PHASE_CONFIRM, 0))
        assert seen["context"] is None


# ---------------------------------------------------------------------------
# Champion confirmation (racing)
# ---------------------------------------------------------------------------


class TestConsiderChallenger:
    def _patch_budget(self, monkeypatch, trainer, results_by_name, calls):
        def fake(strategy, games, context):
            calls.append((strategy.name, games, context))
            fitness, win_rate = results_by_name[strategy.name]
            trainer.last_eval_breakdown = [("Opp", win_rate)]
            return fitness

        monkeypatch.setattr(trainer, "_eval_with_budget", fake)

    def test_first_champion_is_crowned_at_confirmed_fitness(self, monkeypatch):
        trainer = _make_trainer(confirm_games=8)
        calls: list = []
        self._patch_budget(monkeypatch, trainer, {"A": (55.0, 60.0)}, calls)

        trainer._consider_challenger(_make_strategy("A"), screen_fitness=90.0, gen=0)

        assert trainer._best_strategy.name == "A"
        # Confirmed fitness, not the lucky screen estimate, is what's kept.
        assert trainer._best_confirmed == 55.0
        assert trainer._best_win_rate == 60.0
        assert calls == [("A", 8, (_SEED_PHASE_CONFIRM, 0))]

    def test_identical_genome_skips_confirmation(self, monkeypatch):
        trainer = _make_trainer()
        incumbent = _make_strategy("Champ", "Province", "Gold")
        trainer._best_strategy = incumbent
        trainer._best_confirmed = 60.0
        calls: list = []
        self._patch_budget(monkeypatch, trainer, {}, calls)

        clone = _make_strategy("Champ-clone", "Province", "Gold")
        trainer._consider_challenger(clone, screen_fitness=95.0, gen=1)

        assert calls == []
        assert trainer._best_strategy is incumbent

    def test_weak_screen_is_gated_without_spending_budget(self, monkeypatch):
        trainer = _make_trainer(confirm_slack=5.0)
        trainer._best_strategy = _make_strategy("Champ", "Province", "Gold")
        trainer._best_confirmed = 60.0
        calls: list = []
        self._patch_budget(monkeypatch, trainer, {}, calls)

        challenger = _make_strategy("Weak", "Duchy")
        trainer._consider_challenger(challenger, screen_fitness=40.0, gen=1)

        assert calls == []
        assert trainer._best_strategy.name == "Champ"

    def test_challenger_replaces_incumbent_when_confirmed_better(self, monkeypatch):
        trainer = _make_trainer(confirm_games=8)
        trainer._best_strategy = _make_strategy("Champ", "Province", "Gold")
        trainer._best_confirmed = 60.0
        calls: list = []
        self._patch_budget(
            monkeypatch, trainer,
            {"Champ": (58.0, 62.0), "New": (66.0, 70.0)},
            calls,
        )

        trainer._consider_challenger(_make_strategy("New", "Province", "Witch"), 65.0, gen=2)

        assert trainer._best_strategy.name == "New"
        assert trainer._best_confirmed == 66.0
        assert trainer._best_win_rate == 70.0
        # Both were measured, on the same confirmation context (paired games).
        assert calls == [
            ("Champ", 8, (_SEED_PHASE_CONFIRM, 2)),
            ("New", 8, (_SEED_PHASE_CONFIRM, 2)),
        ]

    def test_incumbent_retained_and_its_estimate_refreshed(self, monkeypatch):
        trainer = _make_trainer(confirm_games=8)
        trainer._best_strategy = _make_strategy("Champ", "Province", "Gold")
        trainer._best_confirmed = 60.0
        calls: list = []
        self._patch_budget(
            monkeypatch, trainer,
            {"Champ": (57.0, 61.0), "Lucky": (45.0, 50.0)},
            calls,
        )

        trainer._consider_challenger(_make_strategy("Lucky", "Province", "Witch"), 80.0, gen=3)

        assert trainer._best_strategy.name == "Champ"
        # The incumbent's confirmed fitness was re-measured, not left stale.
        assert trainer._best_confirmed == 57.0
        assert trainer._best_win_rate == 61.0


# ---------------------------------------------------------------------------
# Hall of fame
# ---------------------------------------------------------------------------


class TestHallOfFame:
    def _patch_budget(self, monkeypatch, trainer, fitness=50.0):
        def fake(strategy, games, context):
            trainer.last_eval_breakdown = [("Opp", fitness)]
            return fitness

        monkeypatch.setattr(trainer, "_eval_with_budget", fake)

    def test_champion_joins_panel_and_fitness_is_rebased(self, monkeypatch):
        trainer = _make_trainer(hall_of_fame_size=3)
        trainer._best_strategy = _make_strategy("Champ", "Province", "Gold")
        trainer._best_confirmed = 80.0
        self._patch_budget(monkeypatch, trainer, fitness=52.0)

        trainer._update_hall_of_fame(gen=9)

        assert len(trainer.hall_of_fame) == 1
        assert trainer.hall_of_fame[0].name == "HallOfFame-g10"
        # Confirmed fitness re-measured on the new (harder) panel.
        assert trainer._best_confirmed == 52.0

    def test_duplicate_champion_not_added_twice(self, monkeypatch):
        trainer = _make_trainer(hall_of_fame_size=3)
        trainer._best_strategy = _make_strategy("Champ", "Province", "Gold")
        trainer._best_confirmed = 80.0
        self._patch_budget(monkeypatch, trainer)

        trainer._update_hall_of_fame(gen=9)
        trainer._update_hall_of_fame(gen=19)

        assert len(trainer.hall_of_fame) == 1

    def test_hall_is_capped_dropping_oldest(self, monkeypatch):
        trainer = _make_trainer(hall_of_fame_size=2)
        self._patch_budget(monkeypatch, trainer)

        for gen, cards in enumerate([("Province",), ("Province", "Gold"), ("Province", "Witch")]):
            trainer._best_strategy = _make_strategy(f"Champ{gen}", *cards)
            trainer._best_confirmed = 80.0
            trainer._update_hall_of_fame(gen=gen)

        assert len(trainer.hall_of_fame) == 2
        assert [m.name for m in trainer.hall_of_fame] == ["HallOfFame-g2", "HallOfFame-g3"]

    def test_hall_members_are_added_to_the_eval_panel(self, monkeypatch):
        trainer = _make_trainer(games_per_eval=4)
        opp = _make_strategy("Baseline", "Province")
        trainer.set_baseline_panel([opp])
        hof_member = _make_strategy("HallOfFame-g10", "Province", "Gold")
        trainer.hall_of_fame = [hof_member]

        games_against: dict[str, int] = {"Baseline": 0, "HallOfFame-g10": 0}

        def fake_run_game(first_ai, second_ai, kingdom):
            for ai in (first_ai, second_ai):
                if ai.strategy.name in games_against:
                    games_against[ai.strategy.name] += 1
            return first_ai, {}, None, 0

        monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)
        trainer.evaluate_strategy(_make_strategy("Candidate", "Province"))

        # 4 games split across baseline + hall member
        assert games_against == {"Baseline": 2, "HallOfFame-g10": 2}


# ---------------------------------------------------------------------------
# train() integration: racing end-to-end
# ---------------------------------------------------------------------------


class TestTrainWithRacing:
    def test_champion_fitness_comes_from_confirmation_not_screen(self, monkeypatch):
        """Screens report an inflated 80; the confirmation eval reports 65.
        The returned metrics must carry the confirmed value."""
        trainer = _make_trainer(
            population_size=4,
            generations=1,
            games_per_eval=2,
            refine_games=4,
            confirm_games=8,
            hall_of_fame_size=0,
        )

        def fake(strategy):
            by_budget = {2: 80.0, 4: 70.0, 8: 65.0}
            fitness = by_budget[trainer.games_per_eval]
            trainer.last_eval_breakdown = [("Opp", fitness)]
            return fitness

        monkeypatch.setattr(trainer, "evaluate_strategy", fake)

        best, metrics = trainer.train()

        assert best is not None
        assert metrics["fitness"] == pytest.approx(65.0)
        assert metrics["win_rate"] == pytest.approx(65.0)

    def test_train_resets_hall_of_fame_between_runs(self, monkeypatch):
        trainer = _make_trainer(hall_of_fame_size=3)
        trainer.hall_of_fame = [_make_strategy("Stale", "Province")]

        monkeypatch.setattr(trainer, "evaluate_strategy", lambda s: float("-inf"))
        trainer.train()

        assert trainer.hall_of_fame == []
