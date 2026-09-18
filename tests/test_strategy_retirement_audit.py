import json
from types import SimpleNamespace

import pytest

from scripts import audit_strategy_retirement as audit


PROVENANCE = {
    "source_revision": "current-revision",
    "python_version": "3.14.3",
    "source_fingerprint": "current-source-contents",
}


def report(**changes):
    return {"stage": "screen", "games_per_pairing": 200,
            **PROVENANCE, "results": [], **changes}


@pytest.mark.parametrize("field", ["source_revision", "python_version", "source_fingerprint"])
def test_resume_rejects_changed_provenance_without_modifying_evidence(tmp_path, monkeypatch, field):
    output = tmp_path / "results.json"
    output.write_text(json.dumps(report(**{field: "old"})))
    original = output.read_bytes()
    monkeypatch.setattr(audit, "source_provenance", lambda: PROVENANCE)
    monkeypatch.setattr(audit, "cohorts", lambda: [])
    monkeypatch.setattr("sys.argv", ["audit", "--stage", "screen", "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        audit.main()
    assert error.value.code == 2
    assert output.read_bytes() == original


def test_legacy_results_without_fingerprint_cannot_be_resumed():
    saved = report()
    del saved["source_fingerprint"]
    with pytest.raises(ValueError, match="source_fingerprint"):
        audit.validate_provenance(saved, PROVENANCE, "Saved output")


def test_validation_rejects_screen_from_another_revision(tmp_path, monkeypatch):
    screen = tmp_path / "screen.json"
    screen.write_text(json.dumps(report(source_revision="old")))
    output = tmp_path / "validation.json"
    monkeypatch.setattr(audit, "source_provenance", lambda: PROVENANCE)
    monkeypatch.setattr(audit, "cohorts", lambda: [])
    monkeypatch.setattr("sys.argv", ["audit", "--stage", "validate", "--screen", str(screen),
                                     "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        audit.main()
    assert error.value.code == 2
    assert not output.exists()


def test_matching_resume_keeps_completed_pairings(tmp_path, monkeypatch):
    row = {"key": ["screen", "Board", "Candidate", "Replacement"],
           "cohort": "Board", "candidate": "Candidate", "opponent": "Replacement",
           "games": 200, "wins": 50, "win_rate": .25}
    saved = report(results=[row])
    output = tmp_path / "screen.json"
    output.write_text(json.dumps(saved))
    monkeypatch.setattr(audit, "source_provenance", lambda: PROVENANCE)
    monkeypatch.setattr(audit, "cohorts", lambda: [
        ("Board", None, False, ["Candidate"], "Replacement", [])
    ])

    class NoGames:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return SimpleNamespace()  # Any attempt to run a game fails.

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(audit, "StrategyBattle", NoGames)
    monkeypatch.setattr("sys.argv", ["audit", "--stage", "screen", "--output", str(output)])
    audit.main()
    assert json.loads(output.read_text()) == saved


def test_source_edits_during_evaluation_do_not_append_results(tmp_path, monkeypatch):
    output = tmp_path / "results.json"
    output.write_text(json.dumps(report()))
    original = output.read_bytes()
    monkeypatch.setattr(audit, "source_provenance", lambda: {**PROVENANCE, "source_fingerprint": "edited"})
    with pytest.raises(ValueError, match="Source changed during evaluation"):
        audit.save_report(output, report(results=[{"wins": 100}]), PROVENANCE)
    assert output.read_bytes() == original


def test_source_fingerprint_detects_uncommitted_simulator_edits(tmp_path, monkeypatch):
    code = tmp_path / "dominion" / "simulation.py"
    code.parent.mkdir()
    code.write_text("VALUE = 1\n")
    fingerprint = audit.tournament_fingerprint
    monkeypatch.setattr(audit, "tournament_fingerprint", lambda: fingerprint(tmp_path))
    monkeypatch.setattr(audit.subprocess, "check_output", lambda *a, **k: "unchanged-commit\n")
    before = audit.source_provenance()
    code.write_text("VALUE = 2\n")
    after = audit.source_provenance()
    assert before["source_revision"] == after["source_revision"]
    assert before["source_fingerprint"] != after["source_fingerprint"]
