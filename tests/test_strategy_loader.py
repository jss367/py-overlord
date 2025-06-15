from dominion.strategy.strategy_loader import StrategyLoader


def test_strategy_loader_basic():
    loader = StrategyLoader()
    strategies = loader.list_strategies()
    assert 'Big Money' in strategies

    strategy = loader.get_strategy('Big Money')
    assert strategy.name == 'BigMoney'
