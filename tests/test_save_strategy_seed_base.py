"""Exported champions evolved from a hand-written seed keep the seed's hooks."""

import copy
import importlib.util

from dominion.runner import save_strategy_as_python
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategies.albuquerque_seeds import (
    AlbuquerqueChapelBridgeEngine,
    AlbuquerqueStrategy,
)


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_subclass_is_preserved_as_base(tmp_path):
    strategy = AlbuquerqueChapelBridgeEngine()
    strategy.name = "Evolved"
    strategy.gain_priority = [PriorityRule("Province"), PriorityRule("Silver")]
    strategy.multiplier_priority = [PriorityRule("Bridge")]

    out = tmp_path / "champion.py"
    save_strategy_as_python(strategy, out, "Champion", clean_for_publication=False)
    text = out.read_text()
    assert "import AlbuquerqueChapelBridgeEngine as _SeedBase" in text
    assert "class Champion(_SeedBase):" in text

    module = _load(out)
    champion = module.create_champion()
    assert isinstance(champion, AlbuquerqueStrategy)
    assert [r.card for r in champion.gain_priority] == ["Province", "Silver"]
    assert [r.card for r in champion.multiplier_priority] == ["Bridge"]


def test_plain_strategy_still_exports_enhanced_strategy(tmp_path):
    strategy = EnhancedStrategy()
    strategy.name = "Plain"
    strategy.gain_priority = [PriorityRule("Province")]
    out = tmp_path / "plain.py"
    save_strategy_as_python(strategy, out, "Plain", clean_for_publication=False)
    text = out.read_text()
    assert "class Plain(EnhancedStrategy):" in text
    assert "_SeedBase" not in text
    assert _load(out).create_plain().name == "Plain"


def test_loader_instantiated_seed_is_recognised(tmp_path):
    from dominion.strategy.strategy_loader import StrategyLoader

    strategy = StrategyLoader().get_strategy("Albuquerque Masquerade Bridge Engine")
    out = tmp_path / "loader_champion.py"
    save_strategy_as_python(strategy, out, "LoaderChampion", clean_for_publication=False)
    assert "AlbuquerqueMasqueradeBridgeEngine as _SeedBase" in out.read_text()
    assert isinstance(_load(out).create_loaderchampion(), AlbuquerqueStrategy)


def test_seed_export_serializes_lists_emptied_by_evolution(tmp_path):
    """A list that evolved (or was cleaned) to empty must be written out, or
    the seed's ``__init__`` would restore its own list when the module loads."""
    strategy = AlbuquerqueChapelBridgeEngine()
    strategy.name = "Thin"
    assert strategy.trash_priority and strategy.action_priority
    strategy.trash_priority = []
    strategy.action_priority = []
    strategy.multiplier_priority = []

    out = tmp_path / "thin.py"
    save_strategy_as_python(strategy, out, "Thin", clean_for_publication=False)
    text = out.read_text()
    assert "self.trash_priority = []" in text
    assert "self.action_priority = []" in text
    assert "self.multiplier_priority = []" in text

    champion = _load(out).create_thin()
    assert champion.trash_priority == []
    assert champion.action_priority == []
    assert champion.multiplier_priority == []
    assert [r.card for r in champion.gain_priority] == [
        r.card for r in strategy.gain_priority
    ]


def test_island_champion_subclass_keeps_seed_ancestor_as_base(tmp_path):
    """``island_merge`` loads champions under a throwaway ``champion_<stem>``
    module and the trainer deep-copies that class, so the concrete class is
    not importable; the export must fall back to the nearest seed ancestor."""
    from scripts.island_merge import _load_strategy_from_path

    first = AlbuquerqueChapelBridgeEngine()
    first.name = "Island Champion"
    first.gain_priority = [PriorityRule("Province")]
    island_file = tmp_path / "albuquerque_chapel_bridge_engine_champion.py"
    save_strategy_as_python(first, island_file, "IslandChampion", clean_for_publication=False)

    loaded = _load_strategy_from_path(island_file)
    assert type(loaded).__module__.startswith("champion_")
    merged = copy.deepcopy(loaded)
    merged.name = "Merged"
    merged.gain_priority = [PriorityRule("Province"), PriorityRule("Bridge")]

    out = tmp_path / "merged.py"
    save_strategy_as_python(merged, out, "Merged", clean_for_publication=False)
    text = out.read_text()
    assert (
        "from dominion.strategy.strategies.albuquerque_seeds import "
        "AlbuquerqueChapelBridgeEngine as _SeedBase"
    ) in text
    assert "class Merged(_SeedBase):" in text

    champion = _load(out).create_merged()
    assert isinstance(champion, AlbuquerqueStrategy)
    assert [r.card for r in champion.gain_priority] == ["Province", "Bridge"]
    assert [r.card for r in champion.multiplier_priority] == [
        r.card for r in merged.multiplier_priority
    ]
