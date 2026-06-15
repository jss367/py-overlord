"""Tests for tournament seed-ref collection from island manifests.

Board-derived manifests store ``seed_name`` as a display name (``Reuse ...``, a
trick name, ``Random Island 1``) and a separate resolvable ``seed_ref``. The
tournament's ``--include-seeds`` must collect ``seed_ref`` (skipping None) and
NOT try to resolve the display ``seed_name`` (PR #296 regression)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pytest  # noqa: E402

from island_tournament import (  # noqa: E402
    DEFAULT_BOARD,
    _seed_refs_from_manifest,
    assemble_entrants,
    resolve_tournament_board,
)


def _manifest(islands):
    return {"run_id": "x", "board": "boards/lisbon.txt", "islands": islands}


def test_resolve_board_cli_wins_over_manifest():
    manifest = {"board": "boards/rio.txt"}
    assert resolve_tournament_board("boards/oslo.txt", manifest) == (
        "boards/oslo.txt",
        "CLI",
    )


def test_resolve_board_uses_manifest_when_cli_absent():
    manifest = {"board": "boards/rio.txt"}
    assert resolve_tournament_board(None, manifest) == ("boards/rio.txt", "manifest")


def test_resolve_board_falls_back_to_default_without_manifest():
    # --strategies path: no manifest, no --board.
    assert resolve_tournament_board(None, None) == (DEFAULT_BOARD, "default")


def test_resolve_board_falls_back_when_manifest_lacks_board():
    assert resolve_tournament_board(None, {"islands": []}) == (DEFAULT_BOARD, "default")


def test_keeps_loader_and_library_refs_skips_trick_and_random():
    manifest = _manifest(
        [
            {"seed_name": "Big Money Island", "seed_ref": "Big Money"},
            {"seed_name": "Reuse Lisbon City Engine", "seed_ref": "Lisbon City Engine"},
            {"seed_name": "Some Trick", "seed_ref": None},
            {"seed_name": "Random Island 1", "seed_ref": None},
        ]
    )

    refs, skipped = _seed_refs_from_manifest(manifest)

    assert refs == ["Big Money", "Lisbon City Engine"]
    assert skipped == 2


def test_all_resolvable():
    manifest = _manifest(
        [
            {"seed_name": "Big Money Island", "seed_ref": "Big Money"},
            {"seed_name": "Reuse X", "seed_ref": "X"},
        ]
    )

    refs, skipped = _seed_refs_from_manifest(manifest)

    assert refs == ["Big Money", "X"]
    assert skipped == 0


def test_all_unresolvable():
    manifest = _manifest(
        [
            {"seed_name": "Trick A", "seed_ref": None},
            {"seed_name": "Random Island 1", "seed_ref": None},
        ]
    )

    refs, skipped = _seed_refs_from_manifest(manifest)

    assert refs == []
    assert skipped == 2


class _FakeStrategy:
    def __init__(self, name: str):
        self.name = name


class _FakeLoader:
    """Resolves a ref name to a strategy whose display name equals the ref,
    unless an explicit ref->name mapping is given (to force a name collision)."""

    def __init__(self, names: dict[str, str] | None = None):
        self._names = names or {}

    def get_strategy(self, ref: str):
        return _FakeStrategy(self._names.get(ref, ref))


def test_assemble_entrants_collapses_seed_panel_overlap():
    # Champions (file-like names here resolve to themselves), then seeds, then
    # panel — seeds and panel overlap exactly as on a default Lisbon roster.
    champions = ["champ_a", "champ_b"]
    seeds = ["Big Money", "Lisbon City Engine", "ClerkCollectionColony"]
    panel = ["Big Money", "Lisbon City Engine", "ClerkCollectionColony", "Lisbon City Crusher"]
    refs = champions + seeds + panel

    resolved = assemble_entrants(refs, _FakeLoader())

    names = [n for n, _ in resolved]
    # Overlap collapsed: every entrant unique, first occurrence/order preserved.
    assert names == [
        "champ_a",
        "champ_b",
        "Big Money",
        "Lisbon City Engine",
        "ClerkCollectionColony",
        "Lisbon City Crusher",
    ]
    assert len(set(names)) == len(names)


def test_assemble_entrants_rejects_distinct_refs_with_same_name():
    # Two DISTINCT refs resolve to the same display name -> genuine clash.
    loader = _FakeLoader({"alpha": "Clash", "beta": "Clash"})

    with pytest.raises(ValueError, match="Duplicate display name"):
        assemble_entrants(["alpha", "beta"], loader)


def test_legacy_manifest_without_seed_ref_falls_back_to_seed_name():
    # No island carries a seed_ref key → treat as a pre-seed_ref manifest and
    # preserve the old behavior of resolving seed_name directly.
    manifest = _manifest(
        [
            {"seed_name": "Big Money"},
            {"seed_name": "Lisbon City Engine"},
        ]
    )

    refs, skipped = _seed_refs_from_manifest(manifest)

    assert refs == ["Big Money", "Lisbon City Engine"]
    assert skipped == 0
