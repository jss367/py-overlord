from dominion.strategy.strategy_loader import StrategyLoader


def test_strategy_loader_basic():
    loader = StrategyLoader()
    strategies = loader.list_strategies()
    assert 'Big Money' in strategies

    strategy = loader.get_strategy('Big Money')
    assert strategy.name == 'BigMoney'


def test_strategy_loader_unknown_returns_none():
    loader = StrategyLoader()
    assert loader.get_strategy('No Such Strategy') is None


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
