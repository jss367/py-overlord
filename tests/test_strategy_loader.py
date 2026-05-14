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


def test_inspiring_festival_engine_prioritizes_horse_and_necropolis():
    loader = StrategyLoader()
    strategy = loader.get_strategy("Inspiring Festival Engine")

    action_names = [rule.card for rule in strategy.action_priority]

    assert action_names.index("Horse") < action_names.index("Smithy")
    assert action_names.index("Necropolis") < action_names.index("Smithy")
