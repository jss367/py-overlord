"""Fresh saved-candidate comparisons must preserve fixed policies and paired seeds."""

from dataclasses import asdict
import json

import cloudpickle
import pytest

from dominion.boards.loader import BoardConfig
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.simulation.reflective_strategy_search import board_seed, game_seed, genome_text
from dominion.strategy.strategy_loader import StrategyLoader
from scripts.compare_saved_reflective_candidates import (
    analyze, case_seeds, fresh_cases, interval, run_comparison,
)


@pytest.fixture
def saved_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    board = BoardConfig(["Village", "Smithy"])
    manifest = {"status": "complete", "simulation_fingerprint": tournament_fingerprint(),
                "settings": {"seeds": [1, 2]}, "board": asdict(board), "opponents": ["Big Money"]}
    (source / "experiment.json").write_text(json.dumps(manifest))
    from dominion.simulation.structured_genome import KingdomInfo
    from dominion.simulation.reflective_strategy_search import compile_genome
    proposal_text = genome_text(board_seed(board))
    proposal = compile_genome(proposal_text, KingdomInfo.from_kingdom(board.kingdom_cards))
    control = StrategyLoader().get_strategy("Big Money")
    for seed in (1, 2):
        folder = source / f"seed-{seed}"
        folder.mkdir()
        (folder / "selected-genome.json").write_text(proposal_text)
        (folder / "genetic-strategy.pkl").write_bytes(cloudpickle.dumps(control))
        (folder / "gepa_genetic-strategy.pkl").write_bytes(cloudpickle.dumps(proposal if seed == 1 else control))
        for name in ("evaluation-records.json", "summary.json", "genetic-selection.json", "gepa_genetic-selection.json"):
            (folder / name).write_text("{}")
    return source


def test_namespace_keeps_panels_direct_and_search_runs_separate():
    panels = [case_seeds(fresh_cases(["A", "B"], seed, 20)) for seed in (21, 22)]
    direct = case_seeds(fresh_cases(["Opponent"], 21, 20, direct=True))
    assert len(panels[0]) == 20
    assert not panels[0] & panels[1]
    assert not panels[0] & direct
    with pytest.raises(ValueError, match="seat pairs"):
        fresh_cases(["A"], 21, 3)


def test_real_games_deduplicate_identical_policies_and_account_for_every_game(saved_source, tmp_path):
    output = tmp_path / "result"
    manifest = run_comparison(saved_source, output, games=2)
    assert manifest["status"] == "complete"
    assert manifest["analysis"]["total_simulated_games"] == 12
    assert manifest["analysis"]["unchanged_proposals"] == 1
    assert (output / "runner.py").exists()
    assert manifest["results"][0]["aliases"]["assisted"] == "proposal"
    assert manifest["results"][1]["aliases"]["control"] == "assisted"
    assert manifest["analysis"] == analyze(manifest["results"])
    for result in manifest["results"]:
        panel_seeds = []
        for panel in result["panels"].values():
            rows = panel["matchups"][0]["games"]["rows"]
            assert sorted(row[1] for row in rows) == [0, 1]
            assert rows[0][0] == rows[1][0]
            panel_seeds.append({row[0] for row in rows})
        assert all(seeds == panel_seeds[0] for seeds in panel_seeds)
        direct_seeds = {row[0] for matchup in result["direct"].values() for row in matchup["games"]["rows"]}
        assert not direct_seeds & panel_seeds[0]
    with pytest.raises(ValueError, match="new directory"):
        run_comparison(saved_source, output, games=2)


def test_overlap_and_changed_simulator_are_rejected_before_games(saved_source, tmp_path):
    case = fresh_cases(["Big Money"], 1, 2)[0]
    record = {"games": [{"seed": game_seed(case.seed, 0), "seat": 0}]}
    (saved_source / "seed-1/evaluation-records.json").write_text(json.dumps(record))
    output = tmp_path / "result"
    with pytest.raises(ValueError, match="overlap"):
        run_comparison(saved_source, output, games=2)
    assert not output.exists()
    path = saved_source / "experiment.json"
    manifest = json.loads(path.read_text())
    manifest["simulation_fingerprint"] = "changed"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Simulator inputs"):
        run_comparison(saved_source, output, games=2)


def test_seed_level_uncertainty_includes_unchanged_runs():
    estimate = interval([0, 0, 0.1, 0.2, 0.3])
    assert estimate["mean"] == pytest.approx(0.12)
    assert estimate["ci95"] == pytest.approx([-0.0418886, 0.2818886], abs=1e-5)
    with pytest.raises(ValueError, match="At least two"):
        interval([0.2])
