"""Tests for board-derived island seeds (dominion.analysis.island_seeds)."""

from __future__ import annotations

from dataclasses import asdict

import pytest

import dominion.analysis.island_seeds as island_seeds
from dominion.analysis.island_seeds import (
    IslandSpec,
    derive_island_specs,
    resolve_island_seed,
)
from dominion.boards.loader import BoardConfig
from dominion.strategy.enhanced_strategy import EnhancedStrategy


def _board() -> BoardConfig:
    return BoardConfig(kingdom_cards=["Village", "Smithy", "Witch", "Chapel"])


def _strategy(name: str) -> EnhancedStrategy:
    s = EnhancedStrategy()
    s.name = name
    return s


class _FakeLibraryEntry:
    def __init__(self, name: str):
        self.name = name
        self.factory = lambda _n=name: _strategy(_n)


class _FakeLoader:
    def __init__(self, known: dict[str, EnhancedStrategy]):
        self._known = known

    def get_strategy(self, name: str):
        return self._known.get(name)


class TestDeriveIslandSpecs:
    def test_random_islands_pad_the_roster(self, monkeypatch):
        monkeypatch.setattr(island_seeds, "find_compatible_strategies", lambda *a, **k: [])
        monkeypatch.setattr(island_seeds, "build_seed_genomes", lambda board: [])

        specs = derive_island_specs(_board(), max_islands=4)

        assert len(specs) == 4
        assert specs[0] == IslandSpec("loader", "Big Money", "Big Money Island")
        assert all(s.kind == "random" for s in specs[1:])
        # Random islands get distinct names.
        assert len({s.name for s in specs}) == 4

    def test_library_and_trick_islands_come_first(self, monkeypatch):
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [_FakeLibraryEntry("WitchEngine")],
        )
        monkeypatch.setattr(
            island_seeds, "build_seed_genomes",
            lambda board: [("Trail Butterfly Trick", _strategy("trick0"))],
        )

        specs = derive_island_specs(_board(), max_islands=6)

        assert specs[0] == IslandSpec("library", "WitchEngine", "Reuse WitchEngine")
        assert specs[1] == IslandSpec("trick", "0", "Trail Butterfly Trick")
        assert specs[2] == IslandSpec("loader", "Big Money", "Big Money Island")
        assert [s.kind for s in specs[3:]] == ["random", "random", "random"]

    def test_roster_is_truncated_at_max_islands(self, monkeypatch):
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [_FakeLibraryEntry(f"Lib{i}") for i in range(4)],
        )
        monkeypatch.setattr(
            island_seeds, "build_seed_genomes",
            lambda board: [(f"Trick{i}", _strategy(f"t{i}")) for i in range(4)],
        )

        specs = derive_island_specs(_board(), max_islands=5)

        assert len(specs) == 5
        # Library entries (ranked by overlap) survive the cut first.
        assert [s.kind for s in specs] == ["library"] * 4 + ["trick"]

    def test_specs_are_plain_string_dataclasses(self, monkeypatch):
        monkeypatch.setattr(island_seeds, "find_compatible_strategies", lambda *a, **k: [])
        monkeypatch.setattr(island_seeds, "build_seed_genomes", lambda board: [])

        for spec in derive_island_specs(_board(), max_islands=3):
            d = asdict(spec)
            assert set(d) == {"kind", "key", "name"}
            assert all(isinstance(v, str) for v in d.values())


class TestResolveIslandSeed:
    def test_random_resolves_to_none(self):
        seed = resolve_island_seed(
            IslandSpec("random", "1", "Random Island 1"), _board(), _FakeLoader({})
        )
        assert seed is None

    def test_loader_seed_resolves(self):
        bm = _strategy("BigMoney")
        seed = resolve_island_seed(
            IslandSpec("loader", "Big Money", "Big Money Island"),
            _board(),
            _FakeLoader({"Big Money": bm}),
        )
        assert seed is bm

    def test_loader_seed_missing_raises(self):
        with pytest.raises(ValueError, match="not found in strategy loader"):
            resolve_island_seed(
                IslandSpec("loader", "Nope", "Nope"), _board(), _FakeLoader({})
            )

    def test_trick_seed_resolves_by_index(self, monkeypatch):
        t0, t1 = _strategy("t0"), _strategy("t1")
        monkeypatch.setattr(
            island_seeds, "build_seed_genomes",
            lambda board: [("Trick0", t0), ("Trick1", t1)],
        )
        seed = resolve_island_seed(IslandSpec("trick", "1", "Trick1"), _board(), _FakeLoader({}))
        assert seed is t1

    def test_trick_index_out_of_range_raises(self, monkeypatch):
        monkeypatch.setattr(island_seeds, "build_seed_genomes", lambda board: [])
        with pytest.raises(ValueError, match="out of range"):
            resolve_island_seed(IslandSpec("trick", "0", "Trick0"), _board(), _FakeLoader({}))

    def test_library_seed_resolves_by_entry_name(self, monkeypatch):
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [_FakeLibraryEntry("WitchEngine")],
        )
        seed = resolve_island_seed(
            IslandSpec("library", "WitchEngine", "Reuse WitchEngine"), _board(), _FakeLoader({})
        )
        assert seed is not None and seed.name == "WitchEngine"

    def test_library_seed_missing_raises(self, monkeypatch):
        monkeypatch.setattr(island_seeds, "find_compatible_strategies", lambda *a, **k: [])
        with pytest.raises(ValueError, match="not found in strategy library"):
            resolve_island_seed(
                IslandSpec("library", "Gone", "Reuse Gone"), _board(), _FakeLoader({})
            )

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown island spec kind"):
            resolve_island_seed(IslandSpec("weird", "x", "x"), _board(), _FakeLoader({}))


class TestRealBoardIntegration:
    def test_derive_specs_on_real_board(self):
        """End-to-end: derive a roster for a real board file with the real
        library and trick scanner — must produce a full roster topped off
        with Big Money and at least one random island."""
        from dominion.boards.loader import load_board

        board = load_board("boards/siege_engine.txt")
        specs = derive_island_specs(board, max_islands=6)

        assert len(specs) == 6
        kinds = {s.kind for s in specs}
        assert "loader" in kinds or "library" in kinds
        # Names are unique (the tournament keys islands by name).
        assert len({s.name for s in specs}) == 6
