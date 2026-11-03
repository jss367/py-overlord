"""Hard limits, complete evaluation boundaries and honest experiment costs."""

from copy import deepcopy
import json
import random
from types import SimpleNamespace

import pytest

from dominion.boards.loader import BoardConfig, load_board
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.parallel_games import GameResult, TaskResult
from dominion.simulation.reflective_strategy_search import MatchupEvaluator, board_seed, compile_genome, genome_text, matchup_cases
from dominion.simulation.simulation_budget import SimulationBudget, SimulationBudgetExceeded
from dominion.strategy.strategy_loader import StrategyLoader
from dominion.strategy.strategies.base_strategy import BaseStrategy
from scripts.reflective_evolve import budgeted_selection_cases, run_seed


class StatefulStrategy(BaseStrategy):
    def choose_gain(self, state, player, choices):
        self.calls = getattr(self, "calls", 0) + 1
        if self.calls == 1:
            silver = next((card for card in choices if card is not None and card.name == "Silver"), None)
            if silver is not None:
                return silver
        return super().choose_gain(state, player, choices)


def test_ledger_rejects_overruns_without_changing_accounting():
    budget = SimulationBudget(12)
    budget.consume(4, "reflection")
    budget.consume(6, "genetic")
    with pytest.raises(SimulationBudgetExceeded):
        budget.consume(4, "selection")
    assert budget.snapshot() == {"limit": 12, "completed": 10, "remaining": 2,
                                 "phases": {"reflection": 4, "genetic": 6}}


@pytest.mark.parametrize("workers", [1, 2])
def test_trainer_stops_before_incomplete_generation_and_preserves_reserve(tmp_path, workers):
    board = BoardConfig(["Village", "Smithy"])
    # First cycle: five screens * 2, one refine * 2, confirmation * 2 = 14.
    budget = SimulationBudget(18)
    trainer = GeneticTrainer(
        board.kingdom_cards, board_config=board, population_size=5, generations=10,
        games_per_eval=2, refine_games=2, confirm_games=2,
        confirm_min_games_per_opponent=2, hall_of_fame_size=0,
        simulation_budget=budget, budget_reserve_games=4, workers=workers,
        log_folder=str(tmp_path), eval_seed=11,
    )
    trainer.battle_system.logger.log_frequency = 0
    random.seed(11)
    champion, metrics = trainer.train()
    assert champion is not None, metrics
    assert metrics["final_generation"] == 1
    assert metrics["stop_reason"] == "simulation_budget"
    assert metrics["evaluated_games"] == budget.completed == 14
    assert budget.remaining == 4


@pytest.mark.parametrize("workers", [1, 2])
def test_population_and_minimum_panel_cost_cannot_partially_overrun(tmp_path, workers):
    board = BoardConfig(["Village", "Smithy"])
    budget = SimulationBudget(3)
    trainer = GeneticTrainer(board.kingdom_cards, board_config=board, games_per_eval=1,
                             simulation_budget=budget, workers=workers, log_folder=str(tmp_path))
    strategy = compile_genome(genome_text(board_seed(board)), trainer._kingdom_info)
    trainer.set_baseline_panel([strategy, deepcopy(strategy)])
    try:
        # The legacy evaluator plays at least one game per opponent even if
        # the requested total is one; the hard budget counts that real cost.
        with pytest.raises(SimulationBudgetExceeded):
            trainer.evaluate_population([strategy, deepcopy(strategy)])
        assert budget.completed == trainer.evaluated_games == 0
    finally:
        trainer.close()


def test_matchup_panel_preserves_whole_cases_and_actual_game_counts(tmp_path):
    board = BoardConfig(["Village", "Smithy"])
    opponent = StrategyLoader().get_strategy("Big Money")
    budget = SimulationBudget(2)
    evaluator = MatchupEvaluator(board, {"A": opponent, "B": opponent}, tmp_path,
                                 simulation_budget=budget)
    strategy = compile_genome(genome_text(board_seed(board)), evaluator.info)
    cases = matchup_cases(evaluator.opponents, 1, 2, "validation")
    with pytest.raises(SimulationBudgetExceeded):
        evaluator.panel(strategy, cases)
    assert budget.completed == evaluator.simulated_games == 0
    evaluator.evaluate(strategy, cases[0])
    assert budget.completed == evaluator.simulated_games == 2
    with pytest.raises(SimulationBudgetExceeded):
        evaluator.evaluate(strategy, cases[1])
    assert budget.remaining == 0


@pytest.mark.parametrize("board_path,stateful", [(None, True), ("boards/oslo.txt", False)])
def test_parallel_matchups_match_serial_and_reset_policy_state(tmp_path, board_path, stateful):
    board = load_board(board_path) if board_path else BoardConfig(["Village", "Smithy"])
    opponents = {"Big Money": StrategyLoader().get_strategy("Big Money")}
    serial = MatchupEvaluator(board, opponents, tmp_path / "serial")
    budget = SimulationBudget(8)
    parallel = MatchupEvaluator(board, opponents, tmp_path / "parallel", workers=2,
                                simulation_budget=budget, budget_phase="selection")
    strategy = (board_seed(board).compile_into(StatefulStrategy(), serial.info) if stateful
                else compile_genome(genome_text(board_seed(board)), serial.info))
    case = matchup_cases(opponents, 31, 8, "validation")[0]
    saved = random.getstate()
    try:
        a = serial.evaluate(strategy, case)
        b = parallel.evaluate(strategy, case)
        assert a == b
        assert random.getstate() == saved
        assert budget.snapshot()["phases"] == {"selection": 8}
    finally:
        serial.close()
        parallel.close()


def test_remainder_selection_keeps_every_option_and_opponent_balanced():
    cases = budgeted_selection_cases({"A": None, "B": None}, 19, 4, 3, 57)
    assert [case.games for case in cases] == [8, 8]
    assert 3 * sum(c.games for c in cases) == 48
    assert 57 - 48 < 2 * 3 * 2
    assert [c.seed for c in cases] == [c.seed for c in matchup_cases({"A": None, "B": None}, 19, 4, "validation")]
    with pytest.raises(RuntimeError, match="reserve"):
        budgeted_selection_cases({"A": None}, 19, 4, 3, 11)


def test_budgeted_trainer_rejects_incomplete_worker_results(tmp_path):
    board = BoardConfig(["Village", "Smithy"])
    trainer = GeneticTrainer(board.kingdom_cards, board_config=board, games_per_eval=2,
                             workers=2, simulation_budget=SimulationBudget(4), log_folder=str(tmp_path))
    trainer._pool = SimpleNamespace(
        run=lambda tasks: {task.task_id: TaskResult(task.task_id, [GameResult(0, True, 3, 2, 10)])
                           for task in tasks}, close=lambda: None,
    )
    strategy = compile_genome(genome_text(board_seed(board)), trainer._kingdom_info)
    try:
        with pytest.raises(RuntimeError, match="comparison"):
            trainer.evaluate_strategy(strategy)
        assert trainer.evaluated_games == 1
    finally:
        trainer.close()


def test_matchup_worker_error_cannot_turn_into_a_scored_comparison(tmp_path):
    board = BoardConfig(["Village", "Smithy"])
    opponent = StrategyLoader().get_strategy("Big Money")
    evaluator = MatchupEvaluator(board, {"Big Money": opponent}, tmp_path, workers=2,
                                 simulation_budget=SimulationBudget(4))
    evaluator._pool = SimpleNamespace(run=lambda tasks: {0: RuntimeError("worker unavailable")},
                                      close=lambda: None)
    strategy = compile_genome(genome_text(board_seed(board)), evaluator.info)
    try:
        with pytest.raises(RuntimeError, match="worker failed"):
            evaluator.evaluate(strategy, matchup_cases(evaluator.opponents, 1, 2, "test")[0])
        assert evaluator.records == []
    finally:
        evaluator.close()


def test_matched_runner_accounts_for_both_arms_and_excludes_fresh_games(tmp_path, monkeypatch):
    pytest.importorskip("gepa")
    from dominion.simulation.codex_reflection import CodexReflection

    board = BoardConfig(["Village", "Smithy"])
    text = genome_text(board_seed(board))
    monkeypatch.setattr(CodexReflection, "__init__", lambda self, *args, **kwargs: None)
    monkeypatch.setattr(CodexReflection, "__call__", lambda self, prompt: "```json\n" + text + "\n```")
    for attr in ("total_cost", "total_tokens_in", "total_tokens_out"):
        monkeypatch.setattr(CodexReflection, attr, 0, raising=False)
    args = SimpleNamespace(
        seed_genome=None, reflection_backend="codex", reflection_model=None,
        reflection_timeout=300, max_metric_calls=6, max_reflection_cost=0.5,
        train_games=2, validation_games=2, test_games=2, population=5,
        generations=10, workers=1, search_game_budget=60,
    )
    output = tmp_path / "experiment"
    # Holdout can only begin after both recommendations and search ledgers
    # have been settled; changing held-out outcomes cannot affect selection.
    original = MatchupEvaluator.evaluate
    def evaluate(self, strategy, case, **kwargs):
        if case.split == "test":
            assert self.simulation_budget is None
            assert (output / "genetic-strategy.pkl").exists()
            assert (output / "gepa_genetic-strategy.pkl").exists()
        return original(self, strategy, case, **kwargs)
    monkeypatch.setattr(MatchupEvaluator, "evaluate", evaluate)
    report = run_seed(board, {"Big Money": StrategyLoader().get_strategy("Big Money")}, 1, args, output)
    ledgers = report["search_budgets"]
    assert set(ledgers) == {"genetic", "gepa_genetic"}
    for arm, ledger in ledgers.items():
        assert ledger["limit"] == 60
        assert ledger["completed"] <= 60
        assert ledger["remaining"] < 2 * len(json.loads((output / f"{arm}-selection.json").read_text())["names"])
    assert "reflection" not in ledgers["genetic"]["phases"]
    assert ledgers["gepa_genetic"]["phases"]["reflection"] == report["gepa_cost"]["simulated_games"]
    assert sum(l["phases"]["selection"] for l in ledgers.values()) == report["selection_games"]
    assert report["total_simulated_games"] == sum(l["completed"] for l in ledgers.values()) + 6
    assert report["hybrid_vs_control"]["matchups"][0]["case"]["seed"] != report["held_out"]["genetic"]["matchups"][0]["case"]["seed"]
