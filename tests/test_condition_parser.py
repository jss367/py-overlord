from dominion.strategy.condition_parser import ConditionParser, GameContext

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
