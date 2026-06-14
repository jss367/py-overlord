"""Tests for tournament seed-ref collection from island manifests.

Board-derived manifests store ``seed_name`` as a display name (``Reuse ...``, a
trick name, ``Random Island 1``) and a separate resolvable ``seed_ref``. The
tournament's ``--include-seeds`` must collect ``seed_ref`` (skipping None) and
NOT try to resolve the display ``seed_name`` (PR #296 regression)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from island_tournament import _seed_refs_from_manifest  # noqa: E402


def _manifest(islands):
    return {"run_id": "x", "board": "boards/lisbon.txt", "islands": islands}


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
