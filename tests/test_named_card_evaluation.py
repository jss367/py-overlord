"""Guard the frozen named-decision protocol and retained raw evidence."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts import evaluate_named_card_decisions as study
from scripts import evaluate_named_card_registered as registered


@pytest.mark.parametrize("card", study.CARDS)
def test_four_stage_scenarios_reach_real_decisions_or_declared_absence(card):
    rows = [r for r in study.scenarios() if r["card"] == card]
    assert len(rows) == 8
    assert {r["stage"] for r in rows} == {"early building", "constrained hand", "excessive copies", "endgame"}
    for row in rows:
        if card == "Moneylender" and row["stage"] == "constrained hand":
            assert not row["decisions"] and "Copper" not in row["initial_hand"]
        else:
            assert row["decisions"], row
        if row["stage"] == "excessive copies":
            assert row["initial_hand"][:3] == ["Sir Bailey" if card == "Knights" else card] * 3


@pytest.mark.parametrize("card", study.CARDS)
@pytest.mark.parametrize("policy", study.POLICIES)
def test_instrumentation_preserves_seeded_gameplay(card, policy):
    args = (card, study.OPPONENTS[2], policy, 291234, 0)
    observed = study.run_game(*args)
    plain = study.run_game(*args, observe=False)
    assert {k: v for k, v in observed.items() if k != "decisions"} == {
        k: v for k, v in plain.items() if k != "decisions"
    }


def test_screen_is_locked_before_disjoint_fresh_validation():
    screen_path = Path("scripts/data/named-card-decisions-screen.json")
    screen = json.loads(screen_path.read_text())
    validation = json.loads(Path("scripts/data/named-card-decisions-validation.json").read_text())
    assert screen["phase"] == "screen" and validation["phase"] == "validate"
    assert screen["runner_hashes"] == validation["runner_hashes"]
    assert screen["simulation_fingerprint"] == validation["simulation_fingerprint"]
    for path, digest in validation["runner_hashes"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    assert validation["selection_sha256"] == hashlib.sha256(screen_path.read_bytes()).hexdigest()
    assert screen["recommendations"] == validation["recommendations"]
    old = {r["seed"] for row in screen["comparisons"] for r in row["records"]}
    new = {r["seed"] for row in validation["comparisons"] for r in row["records"]}
    assert not old & new
    for result in (screen, validation):
        assert len(result["comparisons"]) == len(study.CARDS) * len(study.OPPONENTS)
        assert result["total_games"] == sum(len(row["records"]) for row in result["comparisons"])
        for row in result["comparisons"]:
            assert len(row["kingdom"]) == len(set(row["kingdom"])) == 10
            assert all(row[k] == v for k, v in study.summarize(row["records"]).items())
        for card in study.CARDS:
            assert any(row["policies"]["default"]["decisions"] for row in result["comparisons"] if row["card"] == card)


def test_registered_comparisons_preserve_both_engine_identities_and_seats():
    before = json.loads(Path("scripts/data/named-card-registered-before.json").read_text())
    after = json.loads(Path("scripts/data/named-card-registered-after.json").read_text())
    assert before["simulation_fingerprint"] != after["simulation_fingerprint"]
    assert before["runner_hashes"] == after["runner_hashes"]
    assert before["engine_label"] == "f3c2da3adf5cb5a82dac41bdeef84dbbe2dd5578"
    assert len(before["comparisons"]) == len(after["comparisons"]) == len(registered.panel()) * 3
    for old, new in zip(before["comparisons"], after["comparisons"]):
        assert (old["strategy"], old["board"], old["opponent"]) == (new["strategy"], new["board"], new["opponent"])
        assert [(r["seed"], r["seat"]) for r in old["records"]] == [(r["seed"], r["seat"]) for r in new["records"]]
        for seed in {r["seed"] for r in new["records"]}:
            assert {r["seat"] for r in new["records"] if r["seed"] == seed} == {0, 1}
    for path, digest in after["runner_hashes"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest


def test_new_guide_is_registered_and_published_without_changing_old_studies():
    name = "remaining-named-card-decisions-and-rules.html"
    source = Path("dominion/reporting/curated_strategy_guides") / name
    assert source.read_bytes() == (Path("reports/strategies") / name).read_bytes()
    assert name in Path("reports/strategies/index.html").read_text()
