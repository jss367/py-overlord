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
from island_evolve import _canonical_ref, _resolvable_seed_ref  # noqa: E402


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


class _AliasLoader:
    """Loader whose alias key differs from the strategy's canonical ``.name``.

    Models the real Big Money case: ``get_strategy("Big Money").name ==
    "BigMoney"`` and the canonical ``"BigMoney"`` itself round-trips. Any other
    key is unknown (returns None)."""

    _MAP = {"Big Money": "BigMoney", "BigMoney": "BigMoney"}

    def get_strategy(self, ref: str):
        name = self._MAP.get(ref)
        return _FakeStrategy(name) if name is not None else None


def _panel_recorded_name(loader, alias: str) -> str:
    # Mirror what _resolve_panel_names records for a strategy: strategy.name.
    return loader.get_strategy(alias).name


def test_resolvable_seed_ref_canonicalizes_loader_alias():
    loader = _AliasLoader()

    # The seed side, fed the loader alias, must emit the canonical name...
    ref = _resolvable_seed_ref("loader", "Big Money", loader)
    assert ref == "BigMoney"
    # ...which is exactly what the panel side records for the same strategy.
    assert ref == _panel_recorded_name(loader, "Big Money")
    # And it round-trips so the tournament can still re-resolve it.
    assert loader.get_strategy(ref) is not None


def test_resolvable_seed_ref_library_canonicalizes_same_way():
    loader = _AliasLoader()
    assert _resolvable_seed_ref("library", "Big Money", loader) == "BigMoney"


def test_resolvable_seed_ref_trick_and_random_return_none():
    loader = _AliasLoader()
    assert _resolvable_seed_ref("trick", "Big Money", loader) is None
    assert _resolvable_seed_ref("random", "0", loader) is None


def test_resolvable_seed_ref_unknown_loader_key_returns_none():
    loader = _AliasLoader()
    assert _resolvable_seed_ref("loader", "Nonexistent", loader) is None


def test_seed_and_panel_refs_dedupe_after_canonicalization():
    # End-to-end of the bug: seed side and panel side must produce the SAME
    # ref string for the same strategy so assemble_entrants dedupes (one
    # entrant) instead of raising on a "distinct refs, same name" clash.
    loader = _AliasLoader()
    seed_ref = _resolvable_seed_ref("loader", "Big Money", loader)
    panel_name = _panel_recorded_name(loader, "Big Money")

    resolved = assemble_entrants([seed_ref, panel_name], _FakeLoader())

    assert len(resolved) == 1
    assert resolved[0][0] == "BigMoney"


# --- _canonical_ref chokepoint: the single rule every manifest ref obeys ----


def test_canonical_ref_collapses_alias_to_name():
    loader = _AliasLoader()
    assert _canonical_ref("Big Money", loader) == "BigMoney"


def test_canonical_ref_is_idempotent_on_canonical_name():
    loader = _AliasLoader()
    assert _canonical_ref("BigMoney", loader) == "BigMoney"
    # Idempotent: canonicalizing the canonical form is a fixed point.
    assert _canonical_ref(_canonical_ref("Big Money", loader), loader) == "BigMoney"


def test_canonical_ref_passes_through_py_path_unchanged():
    loader = _AliasLoader()
    path = "generated_strategies/island_champions/foo_champion.py"
    assert _canonical_ref(path, loader) == path


def test_canonical_ref_passes_through_unknown_ref_unchanged():
    loader = _AliasLoader()
    assert _canonical_ref("Totally Unknown", loader) == "Totally Unknown"


def test_canonical_ref_falls_back_when_name_does_not_round_trip():
    # alias resolves, but the resolved .name does NOT itself re-resolve ->
    # keep the alias (which we know resolves) rather than emit a dead ref.
    class _OneWayLoader:
        def get_strategy(self, ref):
            if ref == "alias":
                return _FakeStrategy("Pretty Name")  # "Pretty Name" is unknown
            return None

    assert _canonical_ref("alias", _OneWayLoader()) == "alias"


def test_explicit_panel_alias_is_canonicalized():
    # The reported residual: an explicit --panel ["Big Money"] must record
    # "BigMoney" so it can't collide with a canonicalized Big Money seed_ref.
    loader = _AliasLoader()
    recorded = [_canonical_ref(name, loader) for name in ["Big Money"]]
    assert recorded == ["BigMoney"]


def test_explicit_panel_and_seed_dedupe_end_to_end():
    # Full class: a Big Money island seed_ref and an explicit --panel
    # "Big Money" entry both reduce to "BigMoney"; assemble_entrants yields
    # ONE entrant rather than raising on a name clash.
    loader = _AliasLoader()
    seed_ref = _resolvable_seed_ref("loader", "Big Money", loader)
    explicit_panel = [_canonical_ref(name, loader) for name in ["Big Money"]]

    resolved = assemble_entrants([seed_ref, *explicit_panel], _FakeLoader())

    assert len(resolved) == 1
    assert resolved[0][0] == "BigMoney"
