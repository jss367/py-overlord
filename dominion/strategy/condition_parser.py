import operator
from typing import Callable

from lark import Lark, Transformer


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
    ?and_expr: primary (AND primary)*
    
    ?primary: comparison
           | count_check
           | "(" expr ")"
    
    comparison: state_ref OPERATOR number
              | player_ref OPERATOR number
    
    count_check: "my.count(" card_name ")" OPERATOR number
    
    state_ref: "state.turn_number"
             | "state.provinces_left"
             | "state.empty_piles"
    
    player_ref: "my.coins"
              | "my.actions"
              | "my.buys"
              | "my.hand_size"
    
    card_name: CNAME
    number: NUMBER
    
    OPERATOR: "<" | "<=" | ">" | ">=" | "==" | "!="
    
    AND: "AND"
    OR: "OR"
    
    %import common.CNAME
    %import common.NUMBER
    %import common.WS
    %ignore WS
    """

    def __init__(self):
        self.parser = Lark(self.GRAMMAR)
        self.transformer = ConditionTransformer()

    def parse(self, condition: str) -> Callable[[GameContext], bool]:
        """Parse a condition string into a callable that takes a GameContext"""
        if not condition:
            return lambda _: True

        try:
            tree = self.parser.parse(condition)
            return self.transformer.transform(tree)
        except Exception as e:
            raise ValueError(f"Invalid condition syntax: {condition}") from e


class ConditionTransformer(Transformer):
    """Transforms parse tree into callable functions"""

    OPERATORS = {
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        '==': operator.eq,
        '!=': operator.ne,
    }

    def number(self, items):
        return int(items[0])

    def card_name(self, items):
        return str(items[0])

    def state_ref(self, items):
        ref = str(items[0])

        def get_state_value(context: GameContext) -> int:
            if ref == "state.turn_number":
                return context.state.turn_number
            elif ref == "state.provinces_left":
                return context.state.supply.get("Province", 0)
            elif ref == "state.empty_piles":
                return sum(1 for count in context.state.supply.values() if count == 0)
            raise ValueError(f"Unknown state reference: {ref}")

        return get_state_value

    def player_ref(self, items):
        ref = str(items[0])

        def get_player_value(context: GameContext) -> int:
            if ref == "my.coins":
                return context.my.coins
            elif ref == "my.actions":
                return context.my.actions
            elif ref == "my.buys":
                return context.my.buys
            elif ref == "my.hand_size":
                return len(context.my.hand)
            raise ValueError(f"Unknown player reference: {ref}")

        return get_player_value

    def comparison(self, items):
        get_value, op, number = items
        op_func = self.OPERATORS[str(op)]

        def evaluate(context: GameContext) -> bool:
            return op_func(get_value(context), number)

        return evaluate

    def count_check(self, items):
        card_name, op, number = items
        op_func = self.OPERATORS[str(op)]

        def evaluate(context: GameContext) -> bool:
            count = context.my.count_in_deck(card_name)
            return op_func(count, number)

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


# Example usage:
def test_parser():
    parser = ConditionParser()

    # Test simple conditions
    conditions = [
        "my.coins < 3",
        "state.turn_number > 10",
        "my.count(Village) <= 2",
        "my.hand_size >= 5",
        "state.provinces_left == 0",
        "(my.coins >= 8) AND (state.provinces_left > 0)",
        "my.count(Copper) > 4 OR my.count(Silver) > 2",
    ]

    for condition in conditions:
        try:
            evaluator = parser.parse(condition)
            print(f"Successfully parsed: {condition}")
        except Exception as e:
            print(f"Error parsing {condition}: {e}")


if __name__ == "__main__":
    test_parser()
