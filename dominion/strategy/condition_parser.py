import operator
from dataclasses import dataclass
from typing import Any, Callable, Optional

from lark import Lark, Token, Transformer, Tree


class GameContext:
    """Context object providing access to game state during condition evaluation"""

    def __init__(self, state, player):
        self.state = state
        self.my = player


class ConditionParser:
    """Parser for Dominion strategy conditions"""

    GRAMMAR = """
    ?start: expr
    
    ?expr: or_expr
    
    ?or_expr: and_expr (OR and_expr)*
    ?and_expr: atom (AND atom)*
    
    ?atom: comparison
        | count_expr
        | "(" expr ")"
    
    comparison: (STATE_REF | PLAYER_REF) op number
    
    count_expr: "my.count(" CARD_NAME ")" op number
    
    STATE_REF: "state.turn_number"
             | "state.provinces_left"
             | "state.empty_piles"
    
    PLAYER_REF: "my.coins"
              | "my.actions"
              | "my.buys"
              | "my.hand_size"
    
    CARD_NAME: /[A-Z][a-zA-Z]*/
    
    ?op: "<" -> lt
       | "<=" -> le
       | ">" -> gt
       | ">=" -> ge
       | "==" -> eq
       | "!=" -> ne
    
    number: NUMBER
    
    AND: "AND"
    OR: "OR"
    
    %import common.NUMBER
    %import common.WS
    %ignore WS
    """

    def __init__(self):
        self.parser = Lark(self.GRAMMAR, parser='lalr', debug=True)
        self.transformer = ConditionTransformer()

    def parse(self, condition: str) -> Callable[[GameContext], bool]:
        """Parse a condition string into a callable that takes a GameContext"""
        if not condition:
            return lambda _: True

        try:
            tree = self.parser.parse(condition)
            return self.transformer.transform(tree)
        except Exception as e:
            raise ValueError(f"Failed to parse condition '{condition}': {str(e)}")


class ConditionTransformer(Transformer):
    """Transforms parse tree into callable functions"""

    def lt(self, _):
        return operator.lt

    def le(self, _):
        return operator.le

    def gt(self, _):
        return operator.gt

    def ge(self, _):
        return operator.ge

    def eq(self, _):
        return operator.eq

    def ne(self, _):
        return operator.ne

    def number(self, items):
        return int(items[0])

    def STATE_REF(self, items):
        ref = str(items[0])
        print(f"Processing state ref: {ref}, type: {type(ref)}")  # Debug print
        ref_type = ref.split('.')[-1]  # Get last part after dot

        def get_state_value(context: GameContext) -> int:
            print(f"Getting state value for: {ref_type}")  # Debug print
            if ref_type == "turn_number":
                return context.state.turn_number
            elif ref_type == "provinces_left":
                return context.state.supply.get("Province", 0)
            elif ref_type == "empty_piles":
                return sum(1 for count in context.state.supply.values() if count == 0)
            raise ValueError(f"Unknown state reference type: {ref_type} (from {ref})")

        return get_state_value

    def PLAYER_REF(self, items):
        ref = str(items[0])
        print(f"Processing player ref: {ref}, type: {type(ref)}")  # Debug print
        ref_type = ref.split('.')[-1]  # Get last part after dot

        def get_player_value(context: GameContext) -> int:
            print(f"Getting player value for: {ref_type}")  # Debug print
            if ref_type == "coins":
                return context.my.coins
            elif ref_type == "actions":
                return context.my.actions
            elif ref_type == "buys":
                return context.my.buys
            elif ref_type == "hand_size":
                return len(context.my.hand)
            raise ValueError(f"Unknown player reference type: {ref_type} (from {ref})")

        return get_player_value

    def CARD_NAME(self, items):
        return str(items[0])

    def comparison(self, items):
        get_value, op_func, number = items

        def evaluate(context: GameContext) -> bool:
            try:
                print(f"Evaluating comparison with: get_value={get_value}")  # Debug print
                value = get_value(context)
                print(f"Got value: {value}")  # Debug print
                result = op_func(value, number)
                print(f"Comparison result: {value} {op_func.__name__} {number} = {result}")  # Debug print
                return result
            except Exception as e:
                print(f"Error in comparison: {str(e)}")  # Debug print
                raise ValueError(
                    f"Failed to evaluate comparison - "
                    f"op={op_func.__name__}, "
                    f"number={number}, "
                    f"error: {str(e)}"
                )

        return evaluate

    def count_expr(self, items):
        card_name, op_func, number = items

        def evaluate(context: GameContext) -> bool:
            try:
                count = context.my.count_in_deck(card_name)
                return op_func(count, number)
            except Exception as e:
                raise ValueError(f"Failed to evaluate count expression: {str(e)}")

        return evaluate

    def or_expr(self, items):
        if len(items) == 1:
            return items[0]

        def evaluate(context: GameContext) -> bool:
            return any(condition(context) for condition in items)

        return evaluate

    def and_expr(self, items):
        if len(items) == 1:
            return items[0]

        def evaluate(context: GameContext) -> bool:
            return all(condition(context) for condition in items)

        return evaluate


def test_parser():
    parser = ConditionParser()

    # First test: parsing only
    print("\n=== Testing Parser ===")
    test_conditions = [
        "my.coins < 3",
        "state.turn_number > 10",
        "my.count(Village) <= 2",
        "my.hand_size >= 5",
        "state.provinces_left == 0",
        "(my.coins >= 8) AND (state.provinces_left > 0)",
        "my.count(Copper) > 4 OR my.count(Silver) > 2",
    ]

    for condition in test_conditions:
        try:
            parser.parse(condition)
            print(f"✓ Successfully parsed: {condition}")
        except Exception as e:
            print(f"✗ Error parsing {condition}: {str(e)}")

    # Second test: evaluation with tracing
    print("\n=== Testing Evaluation ===")

    class MockState:
        def __init__(self):
            self.turn_number = 5
            self.supply = {"Province": 8}
            print(f"Created MockState with turn_number={self.turn_number}")

    class MockPlayer:
        def __init__(self):
            self.coins = 3
            self.actions = 1
            self.hand = ["Copper", "Copper", "Estate"]
            print(f"Created MockPlayer with coins={self.coins}, actions={self.actions}")

        def count_in_deck(self, card_name):
            count = 2 if card_name == "Copper" else 0
            print(f"count_in_deck({card_name}) = {count}")
            return count

    mock_context = GameContext(MockState(), MockPlayer())

    test_evaluations = ["my.coins >= 3", "state.turn_number < 10", "my.count(Copper) == 2", "my.hand_size == 3"]

    print("\nRunning evaluations:")
    for condition in test_evaluations:
        print(f"\nTesting condition: {condition}")
        try:
            evaluator = parser.parse(condition)
            print("Successfully parsed, now evaluating...")
            result = evaluator(mock_context)
            print(f"✓ Final result: {condition} = {result}")
        except Exception as e:
            print(f"✗ Error: {str(e)}")


if __name__ == "__main__":
    test_parser()
