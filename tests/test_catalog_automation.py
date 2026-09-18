"""Regression coverage for preserving results and staged-only catalog updates."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from dominion.reporting.catalog_pages import render_catalog_pages
from dominion.reporting.html_report import generate_leaderboard_html
from dominion.reporting.strategy_pages import render_strategy_leaderboard
from dominion.reporting.tournament_state import (
    read_snapshot, snapshot_markup, tournament_fingerprint, tournament_notice,
)
from scripts.catalog_pre_commit import refresh_staged_catalog


REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("strict", [False, True])
def test_catalog_check_flags_missing_instructions_without_pythonpath(strict):
    command = [sys.executable, "scripts/check_catalog.py"]
    if strict:
        command.append("--strict-descriptions")
    result = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
    )
    assert result.returncode == int(strict), result.stdout + result.stderr
    assert "custom behaviors without readable instructions" in result.stdout
    assert "Catalog is current" in result.stdout
    assert "Ninja Watchtower Figurine Money:" not in result.stdout


def test_fingerprint_tracks_simulation_inputs_but_not_presentation(tmp_path):
    engine = tmp_path / "dominion/engine.py"
    engine.parent.mkdir()
    engine.write_text("original")
    original = tournament_fingerprint(tmp_path)
    guide = tmp_path / "dominion/reporting/guide.html"
    guide.parent.mkdir()
    guide.write_text("New explanation")
    assert tournament_fingerprint(tmp_path) == original
    engine.write_text("changed")
    assert tournament_fingerprint(tmp_path) != original
    engine.unlink()
    assert tournament_fingerprint(tmp_path) != original


def test_refresh_preserves_tournament_and_ranks_and_marks_changed_inputs(tmp_path, monkeypatch):
    output = tmp_path / "reports"
    leaderboard = output / "strategies/leaderboard.html"
    leaderboard.parent.mkdir(parents=True)
    results = {"BigMoney": {"wins": 7, "losses": 3, "games": 10, "win_rate": 70}}
    generate_leaderboard_html(results, leaderboard, context_label="a saved test tournament")
    saved = read_snapshot(leaderboard)
    obsolete = leaderboard.with_name("removed-strategy.html")
    obsolete.write_text("Old generated page")
    monkeypatch.setattr("dominion.reporting.catalog_pages.tournament_fingerprint", lambda: "changed")
    render_catalog_pages(output, board_paths=[], strategy_names=["Big Money", "Village Smithy Lab"])
    assert read_snapshot(leaderboard) == saved
    assert "Tournament results are outdated" in leaderboard.read_text()
    usage = leaderboard.with_name("card-strategy-usage.html").read_text()
    assert "a saved test tournament" in usage
    assert "Tournament results are outdated" in usage
    assert 'data-label="Median strategy rank" data-sort="1">1</td>' in usage
    assert not obsolete.exists()
    first = {p: p.read_bytes() for p in output.rglob("*.html")}
    render_catalog_pages(output, board_paths=[], strategy_names=["Big Money", "Village Smithy Lab"])
    assert {p: p.read_bytes() for p in output.rglob("*.html")} == first
    # Reverting inputs restores a current label without modifying the evidence.
    monkeypatch.setattr(
        "dominion.reporting.catalog_pages.tournament_fingerprint", lambda: saved["input_fingerprint"],
    )
    render_catalog_pages(output, board_paths=[], strategy_names=["Big Money"])
    assert "Tournament results are outdated" not in leaderboard.read_text()


def test_legacy_standings_are_recovered_without_claiming_freshness(tmp_path):
    path = tmp_path / "leaderboard.html"
    results = {"Big Money": {"wins": 2, "losses": 1, "games": 3, "win_rate": 2 / 3 * 100,
                             "description": "Money & more", "cards": ["Silver", "Gold"]}}
    path.write_text(render_strategy_leaderboard(results, context_label="a historical round robin"))
    saved = read_snapshot(path)
    assert saved["results"] == results
    assert saved["context_label"] == "a historical round robin"
    assert saved["input_fingerprint"] is None
    assert "predate input tracking" in tournament_notice(saved, "current")


def test_saved_json_cannot_close_script_element(tmp_path):
    results = {"</script><script>alert(1)</script>": {"wins": 1}}
    snapshot = {"version": 1, "results": results, "context_label": "test", "input_fingerprint": "abc"}
    markup = snapshot_markup(snapshot)
    assert markup.count("</script>") == 1
    path = tmp_path / "leaderboard.html"
    path.write_text(markup)
    assert read_snapshot(path) == snapshot


@pytest.fixture
def staged_repo(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.STDOUT)

    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Catalog Test")
    (root / "scripts").mkdir()
    # A small renderer makes staging scenarios independent of the simulation.
    (root / "scripts/render_catalog.py").write_text(
        'from pathlib import Path\n'
        'source = Path("boards/example.txt")\n'
        'output = Path("reports/index.html")\n'
        'output.parent.mkdir(exist_ok=True)\n'
        'output.write_text(source.read_text())\n'
        'obsolete = Path("reports/strategies/removed.html")\n'
        'obsolete.unlink(missing_ok=True)\n'
    )
    (root / "boards").mkdir()
    (root / "boards/example.txt").write_text("Original board")
    (root / "reports").mkdir()
    (root / "reports/index.html").write_text("Original board")
    (root / "README.md").write_text("Notes")
    git("add", ".")
    git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "Initial files")
    return root, git


def test_hook_renders_staged_sources_and_never_stages_output(staged_repo):
    root, git = staged_repo
    source = root / "boards/example.txt"
    source.write_text("Staged board")
    git("add", "boards/example.txt")
    source.write_text("Unfinished board edits")
    assert refresh_staged_catalog(root) == 1
    assert (root / "reports/index.html").read_text() == "Staged board"
    assert source.read_text() == "Unfinished board edits"
    assert git("show", ":reports/index.html") == b"Original board"
    git("add", "reports/index.html")
    assert refresh_staged_catalog(root) == 0


def test_hook_preserves_unstaged_report_edits(staged_repo):
    root, git = staged_repo
    (root / "boards/example.txt").write_text("Changed board")
    git("add", "boards/example.txt")
    report = root / "reports/index.html"
    report.write_text("Unfinished report edit")
    assert refresh_staged_catalog(root) == 1
    assert report.read_text() == "Unfinished report edit"


def test_hook_skips_unrelated_commits(staged_repo):
    root, git = staged_repo
    (root / "README.md").write_text("New notes")
    git("add", "README.md")
    # If called, the renderer would fail. This commit doesn't need it.
    (root / "scripts/render_catalog.py").unlink()
    assert refresh_staged_catalog(root) == 0


def test_hook_handles_deleted_pages(staged_repo):
    root, git = staged_repo
    obsolete = root / "reports/strategies/removed.html"
    obsolete.parent.mkdir()
    obsolete.write_text("Removed strategy")
    git("add", "reports/strategies/removed.html")
    assert refresh_staged_catalog(root) == 1
    assert not obsolete.exists()
    git("add", "-u", "reports")
    assert refresh_staged_catalog(root) == 0


def test_hook_preserves_untracked_output_collision(staged_repo):
    root, git = staged_repo
    git("rm", "reports/index.html")
    report = root / "reports/index.html"
    report.parent.mkdir(exist_ok=True)
    report.write_text("Untracked user report")
    assert refresh_staged_catalog(root) == 1
    assert report.read_text() == "Untracked user report"


def test_installer_respects_existing_hook_and_is_repeatable(staged_repo):
    root, git = staged_repo
    hooks = root / "custom hooks"
    hooks.mkdir()
    git("config", "core.hooksPath", str(hooks))
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\necho existing\n")
    installer = [sys.executable, str(REPO / "scripts/install_catalog_hook.py")]
    assert subprocess.run(installer, cwd=root, capture_output=True).returncode == 1
    assert hook.read_text() == "#!/bin/sh\necho existing\n"
    hook.unlink()
    for _ in range(2):
        subprocess.run(installer, cwd=root, check=True, capture_output=True)
    assert hook.stat().st_mode & 0o111
    assert "Dominion catalog refresh hook" in hook.read_text()
    # Older branches without the Python hook continue to work.
    assert subprocess.run([str(hook)], cwd=root).returncode == 0


def test_invalid_snapshot_is_not_silently_discarded(tmp_path):
    path = tmp_path / "leaderboard.html"
    path.write_text('<script type="application/json" id="saved-tournament-results">broken</script>')
    with pytest.raises(json.JSONDecodeError):
        read_snapshot(path)


def test_legacy_recovery_keeps_the_landscapes_a_row_was_indexed_by(tmp_path):
    """A recovered report must not lose Museum and become unfilterable again."""

    path = tmp_path / "leaderboard.html"
    results = {
        "Ninja Watchtower Figurine Money": {
            "wins": 2, "losses": 1, "games": 3, "win_rate": 2 / 3 * 100,
            "description": "Colony and Museum scoring",
            "cards": ["Ninja", "Watchtower"],
            "landscapes": ["Credit", "Museum"],
        }
    }
    path.write_text(render_strategy_leaderboard(results))

    assert read_snapshot(path)["results"] == results
