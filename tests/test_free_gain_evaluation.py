"""Reproduction must preserve existing experiment evidence."""

from pathlib import Path

import pytest

from scripts import evaluate_free_gain_tactics as evaluator


@pytest.mark.parametrize("filename", [
    "free_gain_tactics_evaluation.json",
    "free_gain_tactics_evaluation-2026-10-08.json",
    "free_gain_tactics_evaluation-2026-10-08-exports.json",
    "free_gain_tactics_evaluation-2026-10-08-adapters.json",
    "free_gain_tactics_evaluation-2026-10-08-recording.json",
    "free_gain_tactics_evaluation-2026-10-08-policy-audit.json",
    "free_gain_tactics_evaluation-2026-10-08-committed-recording.json",
])
def test_existing_dated_outcomes_are_rejected_before_simulation(filename, monkeypatch, capsys):
    output = Path("scripts/data") / filename
    before = output.read_bytes()
    monkeypatch.setattr("sys.argv", ["evaluate", "--output", str(output)])
    monkeypatch.setattr(evaluator, "tournament_fingerprint", lambda: pytest.fail("Must reject before starting the panel"))
    with pytest.raises(SystemExit) as error:
        evaluator.main()
    assert error.value.code == 2
    assert "choose a fresh --output path" in capsys.readouterr().err
    assert output.read_bytes() == before


def test_output_created_during_evaluation_is_not_overwritten(tmp_path, monkeypatch):
    output = tmp_path / "reproduction.json"
    monkeypatch.setattr("sys.argv", ["evaluate", "--pairs", "2", "--output", str(output)])
    monkeypatch.setattr(evaluator, "tournament_fingerprint", lambda: "stable")

    class ConcurrentOutputPool:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def map(self, *args):
            output.write_text("other run's evidence")
            return []

    monkeypatch.setattr(evaluator, "ProcessPoolExecutor", ConcurrentOutputPool)
    with pytest.raises(FileExistsError):
        evaluator.main()
    assert output.read_text() == "other run's evidence"
