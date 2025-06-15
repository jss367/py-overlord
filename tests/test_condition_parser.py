from dominion.strategy.condition_parser import ConditionParser, GameContext
import pytest

class MockPlayer:
    def __init__(self):
        self.coins = 3
        self.actions = 1
        self.buys = 1
        self.hand = ['c1', 'c2', 'c3']

    def count_in_deck(self, name: str) -> int:
        return 2 if name == 'Copper' else 0

class MockState:
    def __init__(self):
        self.turn_number = 5
        self.supply = {'Province': 8}


def test_condition_parser_basic_evaluation():
    parser = ConditionParser()
    ctx = GameContext(MockState(), MockPlayer())

    assert parser.parse('my.coins >= 3')(ctx)
    assert parser.parse('state.turn_number < 10')(ctx)
    assert parser.parse('my.count(Copper) == 2')(ctx)
    assert parser.parse('my.hand_size == 3')(ctx)


def test_condition_parser_invalid_syntax():
    parser = ConditionParser()
    with pytest.raises(ValueError):
        parser.parse('my.coins >')


def test_condition_parser_evaluation_error():
    parser = ConditionParser()

    class BadPlayer:
        pass

    ctx = GameContext(MockState(), BadPlayer())
    evaluator = parser.parse('my.actions > 1')
    with pytest.raises(ValueError):
        evaluator(ctx)


def test_condition_parser_empty_condition():
    parser = ConditionParser()
    ctx = GameContext(MockState(), MockPlayer())
    assert parser.parse('')(ctx)
