"""Tests for tournament seed-ref collection from island manifests.

Board-derived manifests store ``seed_name`` as a display name (``Reuse ...``, a
trick name, ``Random Island 1``) and a separate resolvable ``seed_ref``. The
tournament's ``--include-seeds`` must collect ``seed_ref`` (skipping None) and
NOT try to resolve the display ``seed_name`` (PR #296 regression)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from island_tournament import (  # noqa: E402
    DEFAULT_BOARD,
    _seed_refs_from_manifest,
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
