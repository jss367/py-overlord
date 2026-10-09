"""Refuse invalid experiment evidence before dispatching simulations."""

import json
from pathlib import Path

import pytest

from scripts import evaluate_ironworks_engineer as evaluator


def test_existing_evidence_is_preserved_before_simulation(tmp_path, monkeypatch, capsys):
    output = tmp_path / "screen.json"
    output.write_text("previous evidence")
    monkeypatch.setattr("sys.argv", ["evaluate", "--phase", "screen", "--seed", "0", "--output", str(output)])
    monkeypatch.setattr(evaluator, "tournament_fingerprint", lambda: pytest.fail("Existing evidence must be rejected first"))
    with pytest.raises(SystemExit) as error:
        evaluator.main()
    assert error.value.code == 2
    assert "Evidence exists" in capsys.readouterr().err
    assert output.read_text() == "previous evidence"


@pytest.mark.parametrize("problem", ["missing selection", "stale inputs", "overlapping seeds"])
def test_validation_rejects_invalid_selection_before_dispatch(tmp_path, monkeypatch, capsys, problem):
    output = tmp_path / "validation.json"
    selection = tmp_path / "screen.json"
    runner = Path(evaluator.__file__)
    selected = {
        "phase": "screen", "runner_sha256": evaluator.sha256(runner),
        "summary_helper_sha256": evaluator.sha256(runner.with_name("evaluate_card_tactics.py")),
        "simulation_fingerprint": "current", "recommendations": {"Ironworks": "default", "Engineer": "default"},
        "comparisons": [{"records": [{"seed": 100}]}],
    }
    if problem == "stale inputs":
        selected["simulation_fingerprint"] = "previous"
    selection.write_text(json.dumps(selected))
    arguments = ["evaluate", "--phase", "validate", "--pairs", "2", "--seed", "100", "--output", str(output)]
    if problem != "missing selection":
        arguments += ["--selection", str(selection)]
    monkeypatch.setattr("sys.argv", arguments)
    monkeypatch.setattr(evaluator, "tournament_fingerprint", lambda: "current")
    monkeypatch.setattr(evaluator, "ProcessPoolExecutor", lambda **kwargs: pytest.fail("Invalid validation must never launch games"))
    with pytest.raises(SystemExit) as error:
        evaluator.main()
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert {"missing selection": "completed screen", "stale inputs": "inputs must match", "overlapping seeds": "seed ranges overlap"}[problem] in message
    assert not output.exists()
