"""Contracts that keep reflective search inside the simulator's strategy space."""

from dataclasses import asdict, dataclass
import json
import random
import sys
from types import SimpleNamespace

import pytest

from dominion.boards.loader import BoardConfig, load_board
from dominion.simulation.reflective_strategy_search import (
    DominionGEPAAdapter, FailFastReflection, MatchupEvaluator, board_seed, compile_genome,
    genome_text, matchup_cases, optimize_strategy, parse_genome,
)
from dominion.simulation.structured_genome import KingdomInfo
from dominion.strategy.strategy_loader import StrategyLoader


@pytest.fixture
def board():
    return load_board("boards/oslo.txt")


def test_typed_seed_round_trips_and_compiles_without_changing_genome(board):
    genome = board_seed(board)
    text = genome_text(genome)
    info = KingdomInfo.from_kingdom(board.kingdom_cards)
    decoded = parse_genome(text, info)
    strategy = compile_genome(text, info)
    assert asdict(decoded) == asdict(genome)
    assert asdict(strategy._strategic_genome) == asdict(genome)
    assert "Workers' Village" in [target.card for target in decoded.build_targets]
    assert "Magnate" in [target.card for target in decoded.build_targets]
    assert strategy.treasure_priority[-1].card_name == "Bank"


@pytest.mark.parametrize("edit", [
    lambda p: p.update(schema_version=True),
    lambda p: p["genome"].update(code="print('bad')"),
    lambda p: p["genome"]["economy"].update(buy_gold="false"),
    lambda p: p["genome"]["build_targets"][0].update(copies=True),
    lambda p: p["genome"]["build_targets"][0].update(copies=100),
    lambda p: p["genome"]["build_targets"][0].update(card="Wharf"),
    lambda p: p["genome"]["build_targets"][0].update(requires_card="Wharf"),
    lambda p: p["genome"]["build_targets"][0].update(from_turn=9, through_turn=2),
    lambda p: p["genome"]["build_targets"][0].update(priority_band="buy_first"),
    lambda p: p["genome"].update(action_order=["Bank"]),
    lambda p: p["genome"].update(treasure_order=["Gold", "Gold"]),
])
def test_malformed_or_out_of_space_plans_are_rejected(board, edit):
    payload = json.loads(genome_text(board_seed(board)))
    edit(payload)
    with pytest.raises(ValueError):
        parse_genome(json.dumps(payload), KingdomInfo.from_kingdom(board.kingdom_cards))


def test_colony_and_platinum_are_not_available_on_an_ordinary_board():
    board = BoardConfig(["Village", "Smithy"])
    payload = json.loads(genome_text(board_seed(board)))
    payload["genome"]["build_targets"][0]["card"] = "Colony"
    with pytest.raises(ValueError, match="Unavailable"):
        parse_genome(json.dumps(payload), KingdomInfo.from_kingdom(board.kingdom_cards))


def test_case_blocks_are_distinct_and_seat_balanced():
    cases = [matchup_cases({"A": None, "B": None}, 7, 4, split)
             for split in ("train", "validation", "test")]
    assert len({c.seed for panel in cases for c in panel}) == 6
    assert cases[0] == matchup_cases({"A": None, "B": None}, 7, 4, "train")
    with pytest.raises(ValueError):
        matchup_cases({"A": None}, 7, 3, "train")


def test_real_games_are_reproducible_with_loss_trace_and_restore_rng(tmp_path):
    board = BoardConfig(["Village", "Smithy"])
    opponents = {"Big Money": StrategyLoader().get_strategy("Big Money")}
    evaluator = MatchupEvaluator(board, opponents, tmp_path)
    strategy = compile_genome(genome_text(board_seed(board)), evaluator.info)
    case = matchup_cases(opponents, 11, 2, "train")[0]
    state = random.getstate()
    first = evaluator.evaluate(strategy, case, trace=True)
    second = evaluator.evaluate(strategy, case)
    assert random.getstate() == state
    assert first["win_rate"] == second["win_rate"]
    assert [(r["score"], r["opponent_score"]) for r in first["games"]] == [
        (r["score"], r["opponent_score"]) for r in second["games"]]
    assert first["games"][0]["seed"] == first["games"][1]["seed"]
    assert [r["seat"] for r in first["games"]] == [0, 1]
    assert "Summary:" in first["representative_game"]["log_excerpt"]
    assert first["representative_game"]["decision_firings"]["priority_rules"]
    assert evaluator.simulated_games == 4


@dataclass
class Batch:
    outputs: list
    scores: list
    trajectories: list | None = None


def test_bad_candidate_is_feedback_without_running_games(board, tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "gepa.core.adapter", SimpleNamespace(EvaluationBatch=Batch))
    evaluator = MatchupEvaluator(board, {"Reference": None}, tmp_path)
    adapter = DominionGEPAAdapter(evaluator)
    cases = matchup_cases(evaluator.opponents, 1, 2, "train")
    result = adapter.evaluate(cases, {"strategy": "not JSON"}, capture_traces=True)
    assert result.scores == [-1.0]
    assert result.trajectories[0]["error"]
    assert evaluator.simulated_games == 0
    dataset = adapter.make_reflective_dataset({}, Batch([], [], []), [])
    assert dataset == {}


def test_reflective_search_cannot_change_the_experiment_schema(board, tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "gepa.core.adapter", SimpleNamespace(EvaluationBatch=Batch))
    evaluator = MatchupEvaluator(board, {"Reference": None}, tmp_path)
    adapter = DominionGEPAAdapter(evaluator, schema_version=1)
    cases = matchup_cases(evaluator.opponents, 1, 2, "train")
    result = adapter.evaluate(cases, {"strategy": genome_text(board_seed(board))}, capture_traces=True)
    assert result.scores == [-1.0]
    assert "preserve" in result.trajectories[0]["error"]
    assert evaluator.simulated_games == 0


def test_robust_seed_selection_uses_validation_not_gepa_mean(board, tmp_path, monkeypatch):
    evaluator = MatchupEvaluator(board, {"A": None, "B": None}, tmp_path)
    text = genome_text(board_seed(board))
    alternative = json.loads(text)
    alternative["genome"]["economy"]["buy_gold"] = False
    alternative = json.dumps(alternative)
    captured = {}

    def optimize(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            candidates=[{"strategy": text}, {"strategy": alternative}],
            val_subscores=[{0: 1.0, 1: 0.4}, {0: 0.65, 1: 0.65}],
            to_dict=lambda: {},
        )

    monkeypatch.setitem(sys.modules, "gepa", SimpleNamespace(optimize=optimize))
    train = matchup_cases(evaluator.opponents, 1, 2, "train")
    validation = matchup_cases(evaluator.opponents, 1, 2, "validation")
    selected, metadata = optimize_strategy(
        evaluator, text, train, validation, reflection_lm=lambda p: p,
        max_metric_calls=12, run_dir=tmp_path,
    )
    assert selected == alternative
    assert metadata["selected_index"] == 1
    assert captured["trainset"] == train
    assert captured["valset"] == validation
    assert "not instructions or a prompt" in captured["reflection_prompt_template"]
    stop = captured["stop_callbacks"][0]
    assert not stop(SimpleNamespace(total_num_evals=8))
    assert stop(SimpleNamespace(total_num_evals=9))
    with pytest.raises(ValueError, match="training and validation"):
        optimize_strategy(evaluator, text, train,
                          matchup_cases(evaluator.opponents, 1, 2, "test"),
                          reflection_lm=lambda p: p, max_metric_calls=12, run_dir=tmp_path)


def test_reflection_failure_stops_instead_of_producing_a_false_comparison():
    calls = []

    def broken(prompt):
        calls.append(prompt)
        raise RuntimeError("Provider unavailable")

    lm = FailFastReflection(broken)
    with pytest.raises(RuntimeError, match="Provider unavailable"):
        lm("first")
    with pytest.raises(RuntimeError, match="failed earlier"):
        lm("retry")
    with pytest.raises(RuntimeError, match="no valid result"):
        lm.check()
    assert calls == ["first"]


def test_real_gepa_loop_with_test_proposer_and_simulator(tmp_path):
    """Optional-dependency smoke test: no network, no playing-strength claim."""
    pytest.importorskip("gepa")
    board = BoardConfig(["Village", "Smithy"])
    evaluator = MatchupEvaluator(
        board, {"Big Money": StrategyLoader().get_strategy("Big Money")}, tmp_path / "logs",
    )
    text = genome_text(board_seed(board))
    prompts = []

    def reflection(prompt):
        prompts.append(prompt)
        return "```json\n" + text + "\n```"

    selected, metadata = optimize_strategy(
        evaluator, text, matchup_cases(evaluator.opponents, 1, 2, "train"),
        matchup_cases(evaluator.opponents, 1, 2, "validation"),
        reflection_lm=reflection, max_metric_calls=8, run_dir=tmp_path / "gepa",
    )
    assert parse_genome(selected, evaluator.info) == parse_genome(text, evaluator.info)
    assert prompts and "representative_game" in prompts[0]
    assert metadata["result"]["total_metric_calls"] <= 8
    assert evaluator.simulated_games == metadata["result"]["total_metric_calls"] * 2


@pytest.mark.parametrize("backend", ["api", "codex"])
def test_comparison_runner_locks_both_recommendations_before_testing(tmp_path, monkeypatch, backend):
    pytest.importorskip("gepa")
    from gepa import lm
    from scripts.reflective_evolve import run_seed

    board = BoardConfig(["Village", "Smithy"])
    text = genome_text(board_seed(board))

    class TestLM:
        total_cost = total_tokens_in = total_tokens_out = 0

        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, prompt):
            return "```json\n" + text + "\n```"

    monkeypatch.setattr(lm, "LM", TestLM)
    monkeypatch.setattr("dominion.simulation.codex_reflection.CodexReflection", TestLM)
    original_panel = MatchupEvaluator.panel
    output = tmp_path / "experiment"

    def panel(self, strategy, cases, worst_case_weight=0.5):
        if cases[0].split == "test":
            assert (output / "genetic-strategy.pkl").exists()
            assert (output / "gepa_genetic-strategy.pkl").exists()
        return original_panel(self, strategy, cases, worst_case_weight)

    monkeypatch.setattr(MatchupEvaluator, "panel", panel)
    args = SimpleNamespace(
        seed_genome=None, reflection_model="test proposer", max_metric_calls=6,
        max_reflection_cost=0.5, train_games=2, validation_games=2, test_games=2,
        population=5, generations=1, workers=1,
        reflection_backend=backend, reflection_timeout=300,
    )
    report = run_seed(board, {"Big Money": StrategyLoader().get_strategy("Big Money")},
                      1, args, output)
    records = json.loads((output / "evaluation-records.json").read_text())
    assert report["total_simulated_games"] == (
        sum(len(record["games"]) for record in records) + args.test_games
        + report["control_cost"]["evaluated_games"] + report["hybrid_cost"]["evaluated_games"]
    )
    assert report["gepa_metric_calls"] <= args.max_metric_calls
    assert report["gepa_cost"]["billing_mode"] == ("api" if backend == "api" else "chatgpt_subscription")
    assert report["gepa_cost"]["estimated_api_cost_usd"] == (0 if backend == "api" else None)
    assert report["novel_gepa_seed"] is False
    assert report["control_cost"]["evaluated_games"] == report["hybrid_cost"]["evaluated_games"]
    assert report["held_out"]["genetic"]["score"] == report["held_out"]["gepa_genetic"]["score"]
    assert set(report["held_out"]) == {"genetic", "gepa_genetic"}


def test_real_gepa_provider_failure_aborts_after_one_request(tmp_path):
    pytest.importorskip("gepa")
    board = BoardConfig(["Village", "Smithy"])
    evaluator = MatchupEvaluator(board, {"Big Money": StrategyLoader().get_strategy("Big Money")},
                                 tmp_path / "logs")
    calls = []

    def unavailable(prompt):
        calls.append(prompt)
        raise RuntimeError("Test provider unavailable")

    with pytest.raises(RuntimeError, match="no valid result"):
        optimize_strategy(
            evaluator, genome_text(board_seed(board)),
            matchup_cases(evaluator.opponents, 1, 2, "train"),
            matchup_cases(evaluator.opponents, 1, 2, "validation"),
            reflection_lm=unavailable, max_metric_calls=6, run_dir=tmp_path / "gepa",
        )
    assert len(calls) == 1
