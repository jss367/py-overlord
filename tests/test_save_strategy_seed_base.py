"""Exported champions evolved from a hand-written seed keep the seed's hooks."""

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
