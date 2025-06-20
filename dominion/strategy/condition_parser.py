import operator
from typing import Callable

from lark import Lark, Transformer, v_args


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


@v_args(inline=True)
class ConditionTransformer(Transformer):
    def lt(self):
        return operator.lt

    def le(self):
        return operator.le

    def gt(self):
        return operator.gt

    def ge(self):
        return operator.ge

    def eq(self):
        return operator.eq

    def ne(self):
        return operator.ne

    def number(self, token):
        return int(token)

    def STATE_REF(self, token):
        ref = token.value  # Use the full string (e.g., "state.turn_number")
        ref_type = ref.split('.')[-1]

        def get_state_value(context: GameContext) -> int:
            if ref_type == "turn_number":
                return context.state.turn_number
            elif ref_type == "provinces_left":
                return context.state.supply.get("Province", 0)
            elif ref_type == "empty_piles":
                return context.state.empty_piles
            raise ValueError(f"Unknown state reference type: {ref_type} (from {ref})")

        return get_state_value

    def PLAYER_REF(self, token):
        ref = token.value  # Use the full string (e.g., "my.coins")
        ref_type = ref.split('.')[-1]

        def get_player_value(context: GameContext) -> int:
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

    def CARD_NAME(self, token):
        return token.value  # e.g., "Copper"

    def comparison(self, get_value, op_func, number):
        def evaluate(context: GameContext) -> bool:
            try:
                value = get_value(context)
                result = op_func(value, number)
                return result
            except Exception as e:
                raise ValueError(
                    f"Failed to evaluate comparison - "
                    f"op={op_func.__name__}, "
                    f"number={number}, "
                    f"error: {str(e)}"
                )

        return evaluate

    def count_expr(self, card_name, op_func, number):
        def evaluate(context: GameContext) -> bool:
            try:
                count = context.my.count_in_deck(card_name)
                return op_func(count, number)
            except Exception as e:
                raise ValueError(f"Failed to evaluate count expression: {str(e)}")

        return evaluate

    def or_expr(self, *conditions):
        if len(conditions) == 1:
            return conditions[0]

        def evaluate(context: GameContext) -> bool:
            return any(condition(context) for condition in conditions)

        return evaluate

    def and_expr(self, *conditions):
        if len(conditions) == 1:
            return conditions[0]

        def evaluate(context: GameContext) -> bool:
            return all(condition(context) for condition in conditions)

        return evaluate

    # Optionally, if you have wrapper rules:
    def expr(self, condition):
        return condition

    def start(self, condition):
        return condition



