"""Worker-process game evaluation must be a drop-in for the serial path."""

from __future__ import annotations

import random
import threading
from copy import deepcopy

import pytest

from dominion.simulation.genetic_trainer import _SEED_PHASE_SCREEN, GeneticTrainer
from dominion.simulation.parallel_games import chunk_games, resolve_workers
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.rule_pruning import _PRIORITY_LIST_ATTRS
from dominion.strategy.strategies.base_strategy import BaseStrategy

KINGDOM = ["Village", "Smithy", "Market", "Laboratory", "Chapel", "Militia", "Moat", "Workshop", "Festival", "Cellar"]


def _make_strategy(name: str, *gain_cards: str) -> BaseStrategy:
    s = BaseStrategy()
    s.name = name
    s.gain_priority = [PriorityRule(c) for c in gain_cards]
    s.gain_priority.append(PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)))
    s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
    s.action_priority = [PriorityRule(c) for c in gain_cards if c not in {"Province", "Gold", "Silver"}]
    return s


def _population() -> list[BaseStrategy]:
    return [
        _make_strategy("Smithy BM", "Province", "Gold", "Smithy", "Silver"),
        _make_strategy("Village Smithy", "Province", "Gold", "Village", "Smithy", "Silver"),
        _make_strategy("Lab", "Province", "Gold", "Laboratory", "Silver"),
    ]


def _make_trainer(tmp_path, **kwargs) -> GeneticTrainer:
    defaults = dict(
        kingdom_cards=KINGDOM,
        population_size=3,
        generations=1,
        games_per_eval=6,
        eval_seed=4242,
        log_folder=str(tmp_path / "logs"),
    )
    defaults.update(kwargs)
    return GeneticTrainer(**defaults)


def _fired(strategies: list[BaseStrategy]) -> list[dict[str, list[int]]]:
    return [
        {
            attr: [i for i, rule in enumerate(getattr(s, attr)) if getattr(rule, "_fired", False)]
            for attr in _PRIORITY_LIST_ATTRS
        }
        for s in strategies
    ]


def test_resolve_workers_defaults_to_cpu_count_and_clamps():
    assert resolve_workers(1) == 1
    assert resolve_workers(3) == 3
    assert resolve_workers(-2) == 1
    assert resolve_workers(0) >= 1
    assert resolve_workers(None) == resolve_workers(0)


def test_chunk_games_keeps_order_and_covers_every_game():
    games = [(i, 100 + i) for i in range(7)]
    chunks = chunk_games(games, 3)
    assert chunks == [games[0:3], games[3:6], games[6:7]]
    assert chunk_games(games, 0) == [[g] for g in games]


def test_seeded_parallel_evaluation_matches_serial(tmp_path):
    """Same seeds, same games: fitness, breakdown and fired flags must agree."""
    serial = _make_trainer(tmp_path, workers=1)
    parallel = _make_trainer(tmp_path, workers=2, games_per_task=2)
    serial_pop = _population()
    parallel_pop = deepcopy(serial_pop)

    serial._eval_seed_context = (_SEED_PHASE_SCREEN, 0)
    parallel._eval_seed_context = (_SEED_PHASE_SCREEN, 0)
    try:
        serial_fitness = serial.evaluate_population(serial_pop)
        parallel_fitness = parallel.evaluate_population(parallel_pop)
        assert serial_fitness == parallel_fitness
        assert serial.last_population_breakdowns == parallel.last_population_breakdowns
        assert _fired(serial_pop) == _fired(parallel_pop)
        assert any(any(v) for v in _fired(parallel_pop)), "expected some rules to fire"

        # Single-strategy entry point goes through the same pool.
        single = parallel.evaluate_strategy(parallel_pop[0])
        assert single == serial_fitness[0]
        assert parallel.last_eval_breakdown == serial.last_population_breakdowns[0]
    finally:
        parallel.close()
        assert parallel._pool is None


def test_parallel_failure_scores_negative_infinity_without_poisoning_others(tmp_path):
    parallel = _make_trainer(tmp_path, workers=2)
    population = _population()
    population[1].unpicklable = threading.Lock()
    parallel._eval_seed_context = (_SEED_PHASE_SCREEN, 0)
    try:
        fitness = parallel.evaluate_population(population)
    finally:
        parallel.close()
    assert fitness[1] == float("-inf")
    assert parallel.last_population_breakdowns[1] == []
    assert fitness[0] != float("-inf") and fitness[2] != float("-inf")
    assert len(parallel.last_population_breakdowns[0]) == 1


def test_train_with_workers_closes_pool(tmp_path):
    trainer = _make_trainer(tmp_path, workers=2, population_size=4, generations=2, games_per_eval=2)
    random.seed(11)
    best, metrics = trainer.train()
    assert best is not None
    assert "error" not in metrics
    assert trainer._pool is None


def test_parallel_battle_is_reproducible_from_seed_and_complete():
    battle = StrategyBattle(kingdom_cards=KINGDOM, log_frequency=0, workers=2, games_per_task=3)
    try:
        random.seed(2024)
        first = battle.run_battle("Big Money", "Big Money Smithy", 8)
        random.seed(2024)
        second = battle.run_battle("Big Money", "Big Money Smithy", 8)
    finally:
        battle.close()

    assert first["games_played"] == 8
    assert len(first["detailed_results"]) == 8
    assert [g["game_number"] for g in first["detailed_results"]] == list(range(1, 9))
    assert first["strategy1_wins"] + first["strategy2_wins"] == 8
    assert first["strategy1_win_rate"] == pytest.approx(first["strategy1_wins"] / 8 * 100)
    assert first["log_paths"] == [None] * 8

    for key in ("strategy1_wins", "strategy2_wins", "strategy1_total_score", "strategy2_total_score", "decision_firings"):
        assert first[key] == second[key]
    assert first["detailed_results"] == second["detailed_results"]

    # Per-game firings roll up into the battle totals, as in the serial path.
    expected: dict[str, dict[str, int]] = {}
    for game in first["detailed_results"]:
        for list_name, bucket in game["decision_firings"]["strategy2"]["priority_rules"].items():
            for key, count in bucket.items():
                expected.setdefault(list_name, {})[key] = expected.get(list_name, {}).get(key, 0) + count
    assert expected, "expected the opponent's priority rules to fire"
    rolled_up = {
        list_name: bucket
        for list_name, bucket in first["decision_firings"]["strategy2"]["priority_rules"].items()
        if bucket
    }
    assert rolled_up == expected
