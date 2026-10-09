"""Evidence must exercise real choices and preserve the evaluation protocol."""

import hashlib
import json
from pathlib import Path

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import CARD_TYPES
from scripts import evaluate_card_tactics as evaluation
from scripts import render_tactical_inventory as inventory


def scenario(card, stage, policy="default"):
    return next(r for r in evaluation.scenarios()
                if (r["card"], r["stage"], r["policy"]) == (card, stage, policy))


@pytest.mark.parametrize("card", evaluation.CARDS)
@pytest.mark.parametrize("stage", ("early building", "constrained hand", "excessive copies", "endgame"))
def test_stage_scenarios_execute_engine_decisions(card, stage):
    for policy in evaluation.POLICIES:
        row = scenario(card, stage, policy)
        assert sum(row["decisions"].values()) == 1
        assert row["initial"]["hand"]
        if card == "Watchtower":
            assert "Watchtower" in row["hand"]
        elif card == "Clerk":
            assert len(row["hand"]) == len(row["initial"]["hand"]) - 1
            assert len(row["deck"]) == 1
        elif card == "Bounty Hunter":
            assert len(row["exile"]) == len(row["initial"]["exile"]) + 1
        else:
            assert len(row["trash"]) in (1, 2)


def test_scenarios_expose_policy_exceptions_without_claiming_optimality():
    assert scenario("Watchtower", "early building")["trash"] == ["Copper"]
    assert scenario("Watchtower", "early building", "contextual")["trash"] == []
    assert scenario("Watchtower", "excessive copies")["deck"] == ["Smithy"]
    assert scenario("Watchtower", "excessive copies", "contextual")["discard"] == ["Smithy"]
    assert scenario("Clerk", "excessive copies")["deck"] == ["Copper"]
    assert scenario("Clerk", "excessive copies", "contextual")["deck"] == ["Province"]
    assert scenario("Bounty Hunter", "endgame")["coins"] == 0
    assert scenario("Bounty Hunter", "endgame", "contextual")["coins"] == 3


def test_investment_scores_all_remaining_treasures_when_it_trashes_itself():
    assert scenario("Investment", "endgame")["coins"] == 1
    cash_out = scenario("Investment", "endgame", "contextual")
    assert cash_out["trash"] == ["Copper", "Investment"]
    assert cash_out["vp_tokens"] == 2  # Silver and Gold both count.
    repeated = scenario("Investment", "excessive copies")
    assert repeated["vp_tokens"] == 4  # Investment copies form one distinct name.
    assert repeated["trash"] == ["Estate", "Investment"]


def test_matching_seeds_reproduce_both_seats_and_summaries():
    task = ("Bounty Hunter", "Smithy money", 2, 991234)
    first = evaluation.evaluate(task)
    assert first == evaluation.evaluate(task)
    assert len(first["records"]) == 8
    assert first["seed_pairs"] == 2
    assert first["games_per_policy"] == 4
    assert first["delta_95_interval"][0] < first["delta_95_interval"][1]
    assert all(not r["truncated"] for r in first["records"])
    with pytest.raises(ValueError, match="both seats"):
        evaluation.summarize(first["records"][1:])


def test_existing_evidence_rejected_before_games(monkeypatch, capsys):
    path = Path("scripts/data/card_tactics_screen.json")
    original = path.read_bytes()
    monkeypatch.setattr("sys.argv", ["evaluate", "--phase", "screen", "--seed", "1", "--output", str(path)])
    monkeypatch.setattr(evaluation, "tournament_fingerprint", lambda: pytest.fail("No games before rejection"))
    with pytest.raises(SystemExit) as error:
        evaluation.main()
    assert error.value.code == 2
    assert "fresh --output" in capsys.readouterr().err
    assert path.read_bytes() == original


def test_validation_rejects_screen_seed_overlap(tmp_path, monkeypatch, capsys):
    screen_path = Path("scripts/data/card_tactics_screen.json")
    screen = json.loads(screen_path.read_text())
    monkeypatch.setattr(evaluation, "tournament_fingerprint", lambda: screen["simulation_fingerprint"])
    monkeypatch.setattr("sys.argv", ["evaluate", "--phase", "validate", "--pairs", "2",
        "--seed", str(screen["seed"]), "--selection", str(screen_path), "--output", str(tmp_path / "fresh.json")])
    with pytest.raises(SystemExit) as error:
        evaluation.main()
    assert error.value.code == 2
    assert "overlap" in capsys.readouterr().err


def test_inventory_covers_registry_with_scoped_claims_and_real_evidence():
    rows = inventory.inventory()
    assert {name for name, _, _ in rows} == set(CARD_TYPES)
    assert len(rows) == len(CARD_TYPES)
    assert any(a is None for _, _, a in rows)
    for _, expansion, audit in rows:
        assert expansion
        if not audit:
            continue
        assert Path(audit.adapter).exists()
        assert all(hasattr(GeneticAI, hook) for hook in audit.hooks)
        for path in audit.evidence:
            assert Path(path).exists(), path
        if audit.tactical.startswith("Evaluated"):
            assert any(p.endswith(".html") for p in audit.evidence)
    assert inventory.OUTPUT.read_text() == inventory.render()


def test_published_outcomes_have_fresh_validation_and_locked_recommendations():
    screen_path = Path("scripts/data/card_tactics_screen.json")
    screen = json.loads(screen_path.read_text())
    validation = json.loads(Path("scripts/data/card_tactics_validation.json").read_text())
    assert screen["phase"] == "screen" and validation["phase"] == "validate"
    assert validation["selection_sha256"] == evaluation.sha256(screen_path)
    assert screen["runner_sha256"] == validation["runner_sha256"] == evaluation.sha256(Path(evaluation.__file__))
    assert screen["recommendations"] == validation["recommendations"]
    old = {r["seed"] for row in screen["comparisons"] for r in row["records"]}
    new = {r["seed"] for row in validation["comparisons"] for r in row["records"]}
    assert not old & new
    for study in (screen, validation):
        assert len(study["comparisons"]) == len(evaluation.CARDS) * len(evaluation.OPPONENTS)
        assert study["total_games"] == sum(len(row["records"]) for row in study["comparisons"])
        for row in study["comparisons"]:
            summary = evaluation.summarize(row["records"])
            assert all(row[key] == value for key, value in summary.items())
            assert sum(row["policies"]["default"]["decisions"].values()) > 0
    source = Path("dominion/reporting/curated_strategy_guides/card-reactions-investment-and-exile-evaluation.html")
    published = Path("reports/strategies") / source.name
    assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(published.read_bytes()).digest()
    assert source.name in Path("reports/strategies/index.html").read_text()
