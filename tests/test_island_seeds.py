"""Tests for board-derived island seeds (dominion.analysis.island_seeds)."""

from __future__ import annotations

from dataclasses import asdict

import pytest

import dominion.analysis.island_seeds as island_seeds
from dominion.analysis.island_seeds import (
    IslandSpec,
    augment_panel_with_compatible,
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
    def __init__(self, name: str, spec: str | None = None):
        self.name = name
        # The real entry's ``spec`` is its unique ``module:function`` reference;
        # default to a unique-per-name value so distinct fakes stay distinct.
        self.spec = spec if spec is not None else f"fake.module:{name}"
        # ``factory`` yields a strategy whose ``.name`` mirrors the spec, so a
        # test can confirm which entry an island resolved to.
        self.factory = lambda _n=self.spec: _strategy(_n)


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

        # Library specs are keyed by the entry *spec* (module:function), not
        # the display name; the display name is "Reuse <name>".
        assert specs[0] == IslandSpec("library", "fake.module:WitchEngine", "Reuse WitchEngine")
        assert specs[1] == IslandSpec("trick", "0", "Trail Butterfly Trick")
        assert specs[2] == IslandSpec("loader", "Big Money", "Big Money Island")
        assert [s.kind for s in specs[3:]] == ["random", "random", "random"]

    def test_library_entries_sharing_a_name_get_distinct_key_and_name(self, monkeypatch):
        """Two library strategies with the same display name but different
        specs must yield two specs with DISTINCT keys (the specs) AND distinct
        names — otherwise both islands resolve to the same seed and collide on
        output filenames/logs."""
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [
                _FakeLibraryEntry("BigMoneySmithy", spec="m:big_money_smithy"),
                _FakeLibraryEntry("BigMoneySmithy", spec="m:big_money_smithy2"),
            ],
        )
        monkeypatch.setattr(island_seeds, "build_seed_genomes", lambda board: [])

        specs = derive_island_specs(_board(), max_islands=6)
        library_specs = [s for s in specs if s.kind == "library"]

        assert len(library_specs) == 2
        # Distinct keys (the canonical module:function specs).
        assert {s.key for s in library_specs} == {"m:big_money_smithy", "m:big_money_smithy2"}
        # Distinct names (the second "Reuse BigMoneySmithy" is disambiguated).
        assert len({s.name for s in library_specs}) == 2
        assert "Reuse BigMoneySmithy" in {s.name for s in library_specs}

    def test_roster_names_are_unique_even_when_library_names_collide(self, monkeypatch):
        """General invariant: no two islands in a derived roster share a name,
        even when several library entries collide on their display name."""
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [
                _FakeLibraryEntry("Dup", spec=f"m:dup{i}") for i in range(3)
            ],
        )
        monkeypatch.setattr(island_seeds, "build_seed_genomes", lambda board: [])

        specs = derive_island_specs(_board(), max_islands=6)

        assert len({s.name for s in specs}) == len(specs)

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
        # Big Money's slot is reserved in the last position; the strongest
        # informed specs (library entries, ranked by overlap) fill the rest.
        assert [s.kind for s in specs] == ["library"] * 4 + ["loader"]
        assert specs[-1] == IslandSpec("loader", "Big Money", "Big Money Island")

    def test_big_money_kept_when_informed_specs_fill_roster(self, monkeypatch):
        """Regression: when library+trick alone meet/exceed max_islands, the
        Big Money baseline must still be in the returned roster (it used to be
        dropped by the final slice)."""
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [_FakeLibraryEntry(f"Lib{i}") for i in range(3)],
        )
        monkeypatch.setattr(
            island_seeds, "build_seed_genomes",
            lambda board: [(f"Trick{i}", _strategy(f"t{i}")) for i in range(3)],
        )

        # 3 library + 3 trick = 6 informed == max_islands (the bazaar_council case).
        specs = derive_island_specs(_board(), max_islands=6)

        assert len(specs) == 6
        # Big Money is present and in the final reserved slot.
        assert IslandSpec("loader", "Big Money", "Big Money Island") in specs
        assert specs[-1] == IslandSpec("loader", "Big Money", "Big Money Island")
        # Informed specs still lead, in ranked order, truncated to max-1.
        assert [s.kind for s in specs[:-1]] == ["library"] * 3 + ["trick"] * 2
        # No duplicate names.
        assert len({s.name for s in specs}) == len(specs)

    def test_max_islands_one_yields_only_big_money(self, monkeypatch):
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [_FakeLibraryEntry("Lib0")],
        )
        monkeypatch.setattr(
            island_seeds, "build_seed_genomes",
            lambda board: [("Trick0", _strategy("t0"))],
        )

        specs = derive_island_specs(_board(), max_islands=1)

        assert specs == [IslandSpec("loader", "Big Money", "Big Money Island")]

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

    def test_library_seed_resolves_by_entry_spec(self, monkeypatch):
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [_FakeLibraryEntry("WitchEngine")],
        )
        # The library branch matches on the entry spec (module:function), so
        # the spec key is the entry's ``.spec``, not its display name.
        seed = resolve_island_seed(
            IslandSpec("library", "fake.module:WitchEngine", "Reuse WitchEngine"),
            _board(),
            _FakeLoader({}),
        )
        assert seed is not None and seed.name == "fake.module:WitchEngine"

    def test_library_seed_missing_raises(self, monkeypatch):
        monkeypatch.setattr(island_seeds, "find_compatible_strategies", lambda *a, **k: [])
        with pytest.raises(ValueError, match="not found in strategy library"):
            resolve_island_seed(
                IslandSpec("library", "fake.module:Gone", "Reuse Gone"), _board(), _FakeLoader({})
            )

    def test_library_seeds_sharing_a_name_resolve_to_own_strategy(self, monkeypatch):
        """Regression: two library strategies can share a display name but have
        distinct specs (e.g. big_money_smithy and big_money_smithy2 both name
        themselves "BigMoneySmithy"). Keying by spec means each island resolves
        to its OWN strategy rather than both collapsing onto the first match."""
        entry_a = _FakeLibraryEntry("BigMoneySmithy", spec="dominion.strategy.strategies.big_money_smithy:build")
        entry_b = _FakeLibraryEntry("BigMoneySmithy", spec="dominion.strategy.strategies.big_money_smithy2:build")
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: [entry_a, entry_b],
        )

        spec_a = IslandSpec("library", entry_a.spec, "Reuse BigMoneySmithy")
        spec_b = IslandSpec("library", entry_b.spec, "Reuse BigMoneySmithy")

        seed_a = resolve_island_seed(spec_a, _board(), _FakeLoader({}))
        seed_b = resolve_island_seed(spec_b, _board(), _FakeLoader({}))

        # Each island resolves to its own strategy (the factory mirrors the spec).
        assert seed_a is not None and seed_a.name == entry_a.spec
        assert seed_b is not None and seed_b.name == entry_b.spec
        assert seed_a.name != seed_b.name

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown island spec kind"):
            resolve_island_seed(IslandSpec("weird", "x", "x"), _board(), _FakeLoader({}))

    def test_library_resolution_not_truncated_below_derive(self, monkeypatch):
        """Regression: with ``reuse_top_k`` > the old hardcoded 10, derive can
        produce a library spec ranked beyond index 10. resolve must search far
        enough to find it (it previously crashed with ``not found in strategy
        library``). The lookup uses an effectively-unbounded ``top_k``."""
        fake_entries = [_FakeLibraryEntry(f"Lib{i}") for i in range(15)]
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies",
            lambda *a, **k: list(fake_entries),
        )

        specs = derive_island_specs(
            _board(), max_islands=20, reuse_top_k=15, reuse_min_overlap=1
        )
        library_specs = [s for s in specs if s.kind == "library"]
        assert len(library_specs) > 10

        # Every derived library spec must resolve, including ones beyond index 10.
        for spec in library_specs:
            seed = resolve_island_seed(spec, _board(), _FakeLoader({}))
            assert seed is not None and seed.name == spec.key

        # Explicitly confirm an entry beyond the old top_k=10 bound resolves.
        beyond = next(s for s in library_specs if s.key == "fake.module:Lib11")
        seed = resolve_island_seed(beyond, _board(), _FakeLoader({}))
        assert seed is not None and seed.name == "fake.module:Lib11"


class TestAugmentPanelWithCompatible:
    def test_adds_loadable_compatible_and_dedupes(self, monkeypatch):
        compat = [
            _FakeLibraryEntry("BigMoney"),  # dup of a baseline, dropped
            _FakeLibraryEntry("EngineA"),
            _FakeLibraryEntry("Unloadable"),  # loader can't resolve -> skipped
            _FakeLibraryEntry("EngineB"),
        ]
        monkeypatch.setattr(
            island_seeds, "find_compatible_strategies", lambda *a, **k: list(compat)
        )
        loader = _FakeLoader(
            {"BigMoney": _strategy("BigMoney"),
             "EngineA": _strategy("EngineA"),
             "EngineB": _strategy("EngineB")}
        )

        names = augment_panel_with_compatible(_board(), ["BigMoney"], loader)

        # Baseline first, then loadable+new compatible, dup and unloadable dropped.
        assert names == ["BigMoney", "EngineA", "EngineB"]

    def test_real_lisbon_panel_is_stronger_than_big_money_alone(self):
        """On Lisbon the built-in baseline collapses to just Big Money; the
        compatible-library augmentation must add real, loadable opponents so
        the default panel is no longer a single weak opponent. Every name must
        round-trip through StrategyLoader (the merge stage re-resolves them)."""
        from dominion.boards.loader import load_board
        from dominion.strategy.strategy_loader import StrategyLoader

        board = load_board("boards/lisbon.txt")
        loader = StrategyLoader()
        names = augment_panel_with_compatible(board, ["Big Money"], loader)

        assert names != ["Big Money"]
        assert len(names) > 1
        for name in names:
            assert loader.get_strategy(name) is not None


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
