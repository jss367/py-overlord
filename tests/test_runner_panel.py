"""Baseline-panel assembly regression tests for dominion.runner.

Reuse is on by default, so a normal run with no ``--baseline-*`` must train
against the DEFAULT baselines (Big Money + compatible built-ins) ALONGSIDE the
reused strategies — not the reused strategies alone (PR #296 regression)."""

from dominion.runner import merge_baseline_panel


class _Strategy:
    def __init__(self, name: str):
        self.name = name


def test_reuse_augments_default_panel_not_replaces():
    default_panel = [_Strategy("Big Money"), _Strategy("ClerkCollectionColony")]
    reused = [_Strategy("Reused A"), _Strategy("Reused B")]

    panel = merge_baseline_panel(default_panel, reused)
    names = [s.name for s in panel]

    # Default baselines survive...
    assert "Big Money" in names
    assert "ClerkCollectionColony" in names
    # ...alongside the reused strategies (not replaced by them).
    assert "Reused A" in names
    assert "Reused B" in names
    assert names == ["Big Money", "ClerkCollectionColony", "Reused A", "Reused B"]


def test_reuse_dedups_by_name():
    default_panel = [_Strategy("Big Money")]
    reused = [_Strategy("Big Money"), _Strategy("Reused A")]

    panel = merge_baseline_panel(default_panel, reused)
    names = [s.name for s in panel]

    assert names.count("Big Money") == 1
    assert names == ["Big Money", "Reused A"]


def test_no_reuse_keeps_default_panel():
    default_panel = [_Strategy("Big Money"), _Strategy("ClerkCollectionColony")]

    panel = merge_baseline_panel(default_panel, [])

    assert [s.name for s in panel] == ["Big Money", "ClerkCollectionColony"]
