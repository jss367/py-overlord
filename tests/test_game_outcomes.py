"""No evaluation path may turn complete ties or safety caps into wins."""

from copy import deepcopy
import pickle
import random

import cloudpickle
import pytest

from dominion.game.game_state import GAME_TURN_LIMIT, GameState
from dominion.game.outcome import GameOutcome, OutcomeCounts, episode_status
from dominion.game.player_state import PlayerState
from dominion.projects.fleet import Fleet
from dominion.simulation import parallel_games
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.strategies.base_strategy import BaseStrategy
from tests.utils import DummyAI


def state_with_scores(scores=(5, 5), turns=(4, 4), *, capped=False):
    players = [PlayerState(DummyAI()), PlayerState(DummyAI())]
    state = GameState(players, supply={"Province": 1 if capped else 0, "Silver": 40})
    state.log_callback = lambda *_: None
    state.turn_number = GAME_TURN_LIMIT + 1
    for player, score, count in zip(players, scores, turns):
        player.vp_tokens = score
        player.turns_taken = count
    return state


@pytest.mark.parametrize("scores,turns,expected", [
    ((8, 5), (5, 4), ("win", "loss")),
    ((5, 5), (5, 4), ("loss", "win")),
    ((5, 5), (4, 4), ("tie", "tie")),
])
def test_shared_outcome_uses_points_then_turns_without_a_seat_fallback(scores, turns, expected):
    outcome = GameOutcome.from_state(state_with_scores(scores, turns))
    assert tuple(outcome.result_for(i) for i in (0, 1)) == expected
    assert sum(outcome.win_share(i) for i in (0, 1)) == 1
    assert outcome.termination_reason == "province_depleted"
    assert pickle.loads(pickle.dumps(outcome)) == outcome


def test_cap_cannot_be_a_win_or_tie_even_with_a_large_score_lead():
    outcome = GameOutcome.from_state(state_with_scores((100, 0), capped=True))
    assert outcome.winners == ()
    assert outcome.truncated and outcome.termination_reason == "turn_limit"
    for seat in (0, 1):
        assert outcome.result_for(seat) == "truncated"
        assert outcome.win_share(seat) == outcome.reward(seat) == 0


@pytest.mark.parametrize("max_turns", [1, 100, 150])
def test_natural_ending_wins_at_the_same_boundary_as_a_cap(max_turns):
    state = state_with_scores()
    state.turn_number = min(max_turns, GAME_TURN_LIMIT) + 1
    assert episode_status(state, max_turns) == (True, False)
    assert GameOutcome.from_state(state, max_turns).result_for(0) == "tie"


def test_fleet_must_complete_before_a_capped_boundary_is_scored():
    state = state_with_scores()
    for player in state.players:
        player.projects.append(Fleet())
    assert episode_status(state) == (False, False)
    with pytest.raises(ValueError, match="unfinished"):
        GameOutcome.from_state(state)
    for _ in range(40):
        terminated, truncated = episode_status(state)
        assert not truncated
        if terminated:
            break
        state.play_turn()
    assert terminated
    assert [p.turns_taken for p in state.players] == [5, 5]
    assert GameOutcome.from_state(state).termination_reason == "fleet"


def passing_strategy(name):
    strategy = BaseStrategy()
    strategy.name = name
    strategy.gain_priority = []
    strategy.action_priority = []
    strategy.treasure_priority = []
    return strategy


def finish_games(monkeypatch, scenarios):
    """Initialize real games at controlled rule/cap boundaries without playing."""
    original = GameState.initialize_game
    scenarios = iter(scenarios)

    def initialize(state, *args, **kwargs):
        original(state, *args, **kwargs)
        scores, capped = next(scenarios)
        state.phase = "start"
        state.turn_number = GAME_TURN_LIMIT + 1
        state.supply["Province"] = 1 if capped else 0
        for player in state.players:
            seat = 0 if player.ai.strategy.name == "Left" else 1
            player.vp_tokens += scores[seat] - player.get_victory_points()
            player.turns_taken = 4

    monkeypatch.setattr(GameState, "initialize_game", initialize)


class DirectPool:
    """Exercise worker batching and serialized results with controlled end states."""

    def run(self, tasks):
        return {task.task_id: cloudpickle.loads(cloudpickle.dumps(parallel_games.run_game_task(task)))
                for task in tasks}


@pytest.mark.parametrize("workers", [1, 2])
def test_battle_counts_ties_and_caps_in_both_execution_paths(monkeypatch, tmp_path, workers):
    finish_games(monkeypatch, [((5, 3), False), ((4, 4), False), ((100, 0), True)])
    battle = StrategyBattle(kingdom_cards=["Village"], log_frequency=0, workers=workers,
                            log_folder=str(tmp_path))
    for name in ("Left", "Right"):
        battle.strategy_loader.register_strategy(name, lambda name=name: passing_strategy(name))
    monkeypatch.setattr(parallel_games, "_WORKER_BATTLE", battle)
    monkeypatch.setattr(battle, "get_pool", lambda: DirectPool())
    results = battle.run_battle("Left", "Right", 3)
    assert (results["strategy1_wins"], results["strategy2_wins"], results["ties"], results["truncated"]) == (1, 0, 1, 1)
    assert results["strategy1_win_rate"] == 50
    assert results["strategy2_win_rate"] == pytest.approx(100 / 6)
    assert [g["outcome"] for g in results["detailed_results"]] == ["win", "tie", "truncated"]
    assert [g["winner"] for g in results["detailed_results"]] == ["Left", None, None]
    assert results["detailed_results"][-1]["termination_reason"] == "turn_limit"


@pytest.mark.parametrize("workers", [1, 2])
@pytest.mark.parametrize("shaped", [False, True])
def test_trainer_uses_half_ties_and_no_cap_margin_bonus(monkeypatch, tmp_path, workers, shaped):
    finish_games(monkeypatch, [((5, 3), False), ((4, 4), False), ((1000, 0), True)])
    trainer = GeneticTrainer(["Village"], population_size=1, generations=1,
                             games_per_eval=3, workers=workers, shape_rewards=shaped,
                             log_folder=str(tmp_path))
    trainer.set_baseline_panel([passing_strategy("Right")])
    monkeypatch.setattr(parallel_games, "_WORKER_BATTLE", trainer.battle_system)
    monkeypatch.setattr(trainer, "_get_pool", lambda: DirectPool())
    score = trainer.evaluate_strategy(passing_strategy("Left"))
    assert score == pytest.approx((.8 * 75 + .2 * 1) * 2 / 3 if shaped else 50)
    assert trainer.last_eval_breakdown[0][1] == 50
    assert trainer.last_eval_outcomes == [{"opponent": "Right", "wins": 1, "losses": 0,
                                          "ties": 1, "truncated": 1, "games": 3}]


def test_real_spawned_workers_and_serial_battles_retain_cap_outcomes_and_rng(tmp_path):
    snapshots, rng_states = [], []
    for workers in (1, 2):
        with StrategyBattle(kingdom_cards=["Village"], log_frequency=0, workers=workers,
                            log_folder=str(tmp_path)) as battle:
            for name in ("Left", "Right"):
                battle.strategy_loader.register_strategy(name, lambda name=name: passing_strategy(name))
            random.seed(2026)
            snapshots.append(battle.run_battle("Left", "Right", 4))
            rng_states.append(random.getstate())
    assert snapshots[0] == snapshots[1]
    assert rng_states[0] == rng_states[1]
    assert snapshots[0]["truncated"] == 4
    assert snapshots[0]["ties"] == snapshots[0]["strategy1_win_rate"] == snapshots[0]["strategy2_win_rate"] == 0


@pytest.mark.parametrize("result", ["tie", "truncated"])
def test_report_renders_without_any_decisive_games(tmp_path, monkeypatch, result):
    from dominion.reporting import html_report

    monkeypatch.setattr(html_report, "fig_to_base64", lambda *_: "image")
    battle = StrategyBattle(log_frequency=0)
    totals = {"strategy1_name": "Left", "strategy2_name": "Right", "strategy1_wins": 0,
              "strategy2_wins": 0, "ties": int(result == "tie"), "truncated": int(result == "truncated"),
              "games_played": 1, "strategy1_total_score": 4, "strategy2_total_score": 4,
              "detailed_results": [{"game_number": 1, "winner": None, "outcome": result,
                                    "turns": 101, "margin": 0}]}
    battle._finalize_results(totals, 1, [None])
    output = tmp_path / "comparison.html"
    html_report.generate_html_report(totals, output)
    text = output.read_text()
    assert "Decisive-game sign test: p=1.0000" in text
    assert f"ties: {totals['ties']}; capped games: {totals['truncated']}" in text


def test_tournament_keeps_actual_losses_separate_from_ties_and_caps(monkeypatch, tmp_path):
    from compare_all_strategies import _run_full_battle

    battle = StrategyBattle(log_frequency=0)
    monkeypatch.setattr(battle.strategy_loader, "list_strategies", lambda: ["Big Money", "Big Money Smithy"])
    monkeypatch.setattr(battle, "run_battle", lambda *_: {
        "strategy1_wins": 1, "strategy2_wins": 0, "ties": 1, "truncated": 1,
    })
    results = _run_full_battle(battle, 3, None)
    assert results["Big Money"]["wins"] == 1
    assert results["Big Money"]["win_rate"] == 50
    assert results["Big Money Smithy"]["losses"] == 1
    assert results["Big Money Smithy"]["win_rate"] == pytest.approx(100 / 6)
    assert results["Big Money Smithy"]["ties"] == results["Big Money Smithy"]["truncated"] == 1
    from dominion.reporting.html_report import generate_leaderboard_html
    from dominion.reporting.tournament_state import read_snapshot

    output = tmp_path / "leaderboard.html"
    generate_leaderboard_html(results, output)
    assert "1 ties; 1 capped" in output.read_text()
    assert "Capped games are reported separately" in output.read_text()
    assert read_snapshot(output)["results"] == results


def test_counts_and_calibration_round_trip_preserve_outcome_counts():
    from dominion.analysis.calibration import MatchOutcome

    counts = OutcomeCounts()
    for result in ("win", "loss", "tie", "truncated"):
        counts.record(result)
    assert counts.games == 4 and counts.completed == 3 and counts.score_rate == 37.5
    row = MatchOutcome("board", "Left", "Right", 1, 4, ties=1, truncated=1)
    assert row.winrate_a == 37.5
    assert MatchOutcome.from_dict(deepcopy(row.to_dict())) == row
    assert row.to_dict()["interval_method"] == "Hoeffding"
    from dominion.analysis.calibration import render_sanity_report
    report = render_sanity_report([row])
    assert "| 4 | 1 | 1 | 37.5% |" in report
    assert "Hoeffding" in report


@pytest.mark.parametrize("workers", [1, 2])
def test_all_capped_training_evaluations_earn_zero_even_with_shaping(monkeypatch, tmp_path, workers):
    finish_games(monkeypatch, [((1000, 0), True)] * 3)
    trainer = GeneticTrainer(["Village"], population_size=1, generations=1,
                             games_per_eval=3, workers=workers, shape_rewards=True,
                             log_folder=str(tmp_path))
    trainer.set_baseline_panel([passing_strategy("Right")])
    monkeypatch.setattr(parallel_games, "_WORKER_BATTLE", trainer.battle_system)
    monkeypatch.setattr(trainer, "_get_pool", lambda: DirectPool())
    assert trainer.evaluate_strategy(passing_strategy("Left")) == 0
    assert trainer.last_eval_outcomes[0]["truncated"] == 3
    assert trainer.last_eval_breakdown == [("Right", 0, 0, 0)]


@pytest.mark.parametrize("games", [1, 3])
def test_synthetic_hypothesis_reference_does_not_invent_wins_or_losses(games):
    from hypothesis_tester import HypothesisTester

    result = HypothesisTester(games=games).compare({"Reference": lambda: passing_strategy("Left")})
    row = result["variants"][0]
    assert row["wins"] == row["losses"] == row["truncated"] == 0
    assert row["ties"] == games and row["win_rate"] == 50
    assert row["synthetic_reference"]
