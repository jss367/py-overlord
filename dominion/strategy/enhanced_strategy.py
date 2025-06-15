"""Minimal strategy framework used by the tests.

The original project had a much more feature rich implementation, but for the
purposes of the tests bundled with this kata we only require a light-weight
definition of :class:`EnhancedStrategy` and :class:`PriorityRule` along with a
few helper constructors.  The strategy creation functions at the bottom of this
file build on these classes.
"""

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class PriorityRule:
    """Represents a single priority rule.

    The ``condition`` field is stored as a simple string; the surrounding code
    does not evaluate these expressions so there is no need for a full parser
    here.  Helper static methods are provided to build commonly used
    conditions.
    """

    card: str
    condition: Optional[str] = None

    @property
    def card_name(self) -> str:
        return self.card

    # Helper constructors -------------------------------------------------
    @staticmethod
    def provinces_left(op: str, amount: int) -> str:
        return f"state.provinces_left {op} {amount}"

    @staticmethod
    def turn_number(op: str, amount: int) -> str:
        return f"state.turn_number {op} {amount}"

    @staticmethod
    def resources(res: str, op: str, amount: int) -> str:
        return f"my.{res} {op} {amount}"

    @staticmethod
    def has_cards(cards: Iterable[str], amount: int) -> str:
        return f"count({'/'.join(cards)}) >= {amount}"

    @staticmethod
    def always_true() -> str:
        return "True"

    @staticmethod
    def and_(*conds: Optional[str]) -> str:
        return " and ".join(c for c in conds if c)

    @staticmethod
    def or_(*conds: Optional[str]) -> str:
        return " or ".join(c for c in conds if c)


class EnhancedStrategy:
    """Base strategy container.

    It simply keeps ordered lists of :class:`PriorityRule` objects that the
    engine can later interpret.
    """

    def __init__(self) -> None:
        self.name: str = "Unnamed"
        self.description: str = ""
        self.version: str = "1.0"

        self.gain_priority: list[PriorityRule] = []
        self.action_priority: list[PriorityRule] = []
        self.trash_priority: list[PriorityRule] = []
        self.treasure_priority: list[PriorityRule] = []

    # ------------------------------------------------------------------
    # Basic decision helpers
    def _eval_condition(self, condition: Optional[str], state, player) -> bool:
        """Evaluate a priority rule condition without using ``eval`` on untrusted code."""
        if not condition:
            return True

        import ast
        import re

        expr = condition

        # Replace logical operators
        expr = expr.replace("AND", "and").replace("OR", "or")

        # Substitute card counts directly into the expression
        def repl(match: re.Match) -> str:
            name = match.group(1)
            names = [n.strip() for n in name.split("/")]
            total = sum(player.count_in_deck(n) for n in names)
            return str(total)

        expr = re.sub(r"my\.count\(([^)]+)\)", repl, expr)

        # Map known references to variable names.  These variables will be
        # provided when evaluating the expression, avoiding use of object
        # attributes inside the parsed AST.
        expr = expr.replace("my.coins", "coins")
        expr = expr.replace("my.actions", "actions")
        expr = expr.replace("my.buys", "buys")
        expr = expr.replace("my.hand_size", "hand_size")
        expr = expr.replace("state.turn_number", "turn_number")
        expr = expr.replace("state.provinces_left", "provinces_left")
        expr = expr.replace("state.empty_piles", "empty_piles")

        variables = {
            "coins": player.coins,
            "actions": player.actions,
            "buys": player.buys,
            "hand_size": len(player.hand),
            "turn_number": state.turn_number,
            "provinces_left": state.supply.get("Province", 0),
            "empty_piles": state.empty_piles,
        }

        try:
            tree = ast.parse(expr, mode="eval")
        except Exception:
            return False

        allowed_nodes = (
            ast.Expression,
            ast.BoolOp,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            ast.Constant,
            ast.Num,
            ast.And,
            ast.Or,
            ast.Add,
            ast.Sub,
            ast.UAdd,
            ast.USub,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                return False
            if isinstance(node, ast.Name) and node.id not in variables:
                return False
            if isinstance(node, (ast.Call, ast.Attribute)):
                return False

        try:
            return bool(eval(compile(tree, "<condition>", "eval"), {"__builtins__": None}, variables))
        except Exception:
            return False

    def _choose_from_priority(self, priority, choices, state, player):
        for rule in priority:
            for card in choices:
                if card is not None and card.name == rule.card and self._eval_condition(rule.condition, state, player):
                    return card
        return None

    # ------------------------------------------------------------------
    def choose_action(self, state, player, choices):
        return self._choose_from_priority(self.action_priority, choices, state, player)

    def choose_treasure(self, state, player, choices):
        return self._choose_from_priority(self.treasure_priority, choices, state, player)

    def choose_gain(self, state, player, choices):
        return self._choose_from_priority(self.gain_priority, choices, state, player)

    def choose_trash(self, state, player, choices):
        return self._choose_from_priority(self.trash_priority, choices, state, player)


def create_big_money_strategy() -> EnhancedStrategy:
    """Classic Big Money strategy focusing on treasure acquisition."""
    strategy = EnhancedStrategy()
    strategy.name = "BigMoney"

    # Gain priorities
    strategy.gain_priority = [
        # Buy Province if we can afford it
        PriorityRule("Province"),
        # Buy Duchy late game
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
        # Buy Gold if we can afford it
        PriorityRule("Gold"),
        # Buy Silver if we can afford it and it's not too late
        PriorityRule("Silver", PriorityRule.provinces_left(">", 2)),
    ]

    # Simple treasure playing order
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]

    return strategy


def create_chapel_witch_strategy() -> EnhancedStrategy:
    """Chapel/Witch engine strategy."""
    strategy = EnhancedStrategy()
    strategy.name = "ChapelWitch"

    # Action priorities
    strategy.action_priority = [
        # Chapel early for deck thinning
        PriorityRule(
            "Chapel",
            PriorityRule.and_(
                PriorityRule.turn_number("<=", 6),
                PriorityRule.or_(PriorityRule.has_cards(["Copper"], 1), PriorityRule.has_cards(["Estate"], 1)),
            ),
        ),
        # Village for actions
        PriorityRule("Village", PriorityRule.resources("actions", "<", 2)),
        # Witch for attacks
        PriorityRule(
            "Witch", PriorityRule.and_(PriorityRule.turn_number(">=", 3), PriorityRule.resources("actions", ">=", 1))
        ),
        # Laboratory for draw
        PriorityRule("Laboratory", PriorityRule.always_true),
    ]

    # Gain priorities
    strategy.gain_priority = [
        # Victory cards
        PriorityRule("Province"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 5)),
        # Engine pieces
        PriorityRule(
            "Witch",
            PriorityRule.and_(
                PriorityRule.turn_number("<", 15), PriorityRule.has_cards(["Witch"], 0)
            ),
        ),
        PriorityRule(
            "Chapel",
            PriorityRule.and_(
                PriorityRule.turn_number("<=", 4), PriorityRule.has_cards(["Chapel"], 0)
            ),
        ),
        PriorityRule(
            "Laboratory",
            PriorityRule.and_(
                PriorityRule.turn_number("<", 12),
                PriorityRule.resources("actions", ">=", 1),
            ),
        ),
        PriorityRule(
            "Village",
            PriorityRule.and_(
                PriorityRule.turn_number("<", 12),
                PriorityRule.has_cards(["Village", "Laboratory", "Witch"], 2),
            ),
        ),
        # Treasure
        PriorityRule("Gold"),
        PriorityRule("Silver", PriorityRule.turn_number("<", 10)),
    ]

    # Treasure priorities
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]

    # Trash priorities
    strategy.trash_priority = [
        PriorityRule("Curse"),
        PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
        PriorityRule(
            "Copper",
            PriorityRule.and_(PriorityRule.has_cards(["Silver", "Gold"], 3), PriorityRule.turn_number("<", 10)),
        ),
    ]

    return strategy


def create_village_smithy_lab_strategy() -> EnhancedStrategy:
    """Village/Smithy/Laboratory engine strategy."""
    strategy = EnhancedStrategy()
    strategy.name = "VillageSmithyLab"

    # Action priorities
    strategy.action_priority = [
        # Village first if low on actions
        PriorityRule("Village", PriorityRule.resources("actions", "<", 2)),
        # Laboratory for efficient draw
        PriorityRule("Laboratory", PriorityRule.resources("actions", ">=", 1)),
        # Smithy for draw
        PriorityRule("Smithy", PriorityRule.resources("actions", ">=", 1)),
    ]

    # Gain priorities
    strategy.gain_priority = [
        # Victory cards
        PriorityRule("Province"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
        # Engine pieces
        PriorityRule("Laboratory", PriorityRule.turn_number("<", 15)),
        PriorityRule("Village", PriorityRule.turn_number("<", 12)),
        PriorityRule("Smithy", PriorityRule.turn_number("<", 12)),
        # Treasure
        PriorityRule("Gold"),
        PriorityRule("Silver", PriorityRule.turn_number("<", 8)),
    ]

    # Treasure priorities
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]

    return strategy
