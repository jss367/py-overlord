from pathlib import Path
import sys
from types import ModuleType

import pytest

from dominion.strategy.strategy_loader import StrategyLoader
from tests.strategy_discovery_probe import catalog_snapshot, make_shadow_package, probe_discovery


def test_strategy_loader_basic():
    loader = StrategyLoader()
    strategies = loader.list_strategies()
    assert 'Big Money' in strategies

    strategy = loader.get_strategy('Big Money')
    assert strategy.name == 'BigMoney'


def test_strategy_loader_unknown_returns_none():
    loader = StrategyLoader()
    assert loader.get_strategy('No Such Strategy') is None
    assert loader.get_strategy_factory('No Such Strategy') is None


def test_strategy_loader_discovery_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    expected = StrategyLoader()
    assert expected.get_strategy("mine_guildhall") is not None

    # An unrelated directory must neither hide the bundled generated strategies
    # nor introduce its own factories into the default catalog.
    local_generated = tmp_path / "generated_strategies"
    local_generated.mkdir()
    (local_generated / "local.py").write_text(
        "from dominion.strategy.enhanced_strategy import EnhancedStrategy\n"
        "def create_working_directory_only() -> EnhancedStrategy:\n"
        "    return EnhancedStrategy()\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    actual = StrategyLoader()

    assert actual.list_strategies(include_retired=True) == expected.list_strategies(include_retired=True)
    assert actual.list_retired_strategies() == expected.list_retired_strategies()
    assert {
        alias: (factory.__module__, factory.__qualname__)
        for alias, factory in actual.strategies.items()
    } == {
        alias: (factory.__module__, factory.__qualname__)
        for alias, factory in expected.strategies.items()
    }
    assert actual.get_strategy("mine_guildhall").name == expected.get_strategy("mine_guildhall").name


@pytest.mark.parametrize("regular", [False, True], ids=["namespace-sibling", "regular-package"])
def test_fresh_process_pins_generated_imports_to_checkout(tmp_path, regular):
    root = Path(__file__).resolve().parents[1]
    make_shadow_package(tmp_path, regular=regular)
    assert probe_discovery(root, tmp_path) == catalog_snapshot(StrategyLoader())


@pytest.mark.parametrize("origin", [None, "/unrelated/generated_strategies/__init__.py"])
def test_strategy_loader_rejects_an_already_imported_foreign_generated_package(monkeypatch, origin):
    foreign = ModuleType("generated_strategies")
    foreign.__file__ = origin
    monkeypatch.setitem(sys.modules, "generated_strategies", foreign)

    with pytest.raises(ImportError, match="generated_strategies is already imported"):
        StrategyLoader()


def test_strategy_loader_exposes_resolved_factory():
    loader = StrategyLoader()

    factory = loader.get_strategy_factory("Big Money")

    assert factory is not None
    assert factory().name == loader.get_strategy("Big Money").name


def test_strategy_loader_display_name_for_aliases():
    loader = StrategyLoader()
    assert loader.get_display_name("BigMoney") == "Big Money"
    assert loader.get_display_name("bigmoney") == "Big Money"
    assert loader.get_display_name("ChapelWitch") == "Chapel Witch"
    assert loader.get_display_name("No Such Strategy") is None


def test_strategy_loader_resolves_duplicate_factories_in_filename_order(tmp_path):
    strategy_module = """
from dominion.strategy.enhanced_strategy import EnhancedStrategy


def create_duplicate() -> EnhancedStrategy:
    strategy = EnhancedStrategy()
    strategy.name = "Duplicate"
    strategy.version = "{version}"
    return strategy
"""
    # Create the files in reverse lexical order to ensure directory iteration
    # order cannot choose the winning factory.
    (tmp_path / "z_strategy.py").write_text(
        strategy_module.format(version="z"), encoding="utf-8"
    )
    (tmp_path / "a_strategy.py").write_text(
        strategy_module.format(version="a"), encoding="utf-8"
    )

    loader = StrategyLoader.__new__(StrategyLoader)
    loader.strategies = {}
    loader._display_names = set()
    loader._load_from_directory(tmp_path, "test_strategies")

    assert loader.get_strategy("Duplicate").version == "z"


def test_inspiring_festival_engine_prioritizes_horse_and_necropolis():
    loader = StrategyLoader()
    strategy = loader.get_strategy("Inspiring Festival Engine")

    action_names = [rule.card for rule in strategy.action_priority]

    assert action_names.index("Horse") < action_names.index("Smithy")
    assert action_names.index("Necropolis") < action_names.index("Smithy")
