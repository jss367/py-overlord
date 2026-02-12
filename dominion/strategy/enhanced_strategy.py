"""Minimal strategy framework used by the tests.

The original project had a much more feature rich implementation, but for the
purposes of the tests bundled with this kata we only require a light-weight
definition of :class:`EnhancedStrategy` and :class:`PriorityRule` along with a
few helper constructors.  The strategy creation functions at the bottom of this
file build on these classes.
"""

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, ClassVar

from dominion.game.card import Card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


@dataclass
class PriorityRule:
    """Represents a single priority rule.

    The ``condition`` field is stored as a simple string; the surrounding code
    does not evaluate these expressions so there is no need for a full parser
    here.  Helper static methods are provided to build commonly used
    conditions.
    """

    card: str
    # Condition is an optional callable that receives (state, player) and returns a bool.
    condition: Optional[Callable[["GameState", "PlayerState"], bool]] = None

    @property
    def card_name(self) -> str:
        return self.card

    # Helper constructors -------------------------------------------------
    import operator as _op

    _OP_MAP: ClassVar[dict[str, Callable[[int, int], bool]]] = {
        "<": _op.lt,
        "<=": _op.le,
        ">": _op.gt,
        ">=": _op.ge,
        "==": _op.eq,
        "!=": _op.ne,
    }

    @staticmethod
    def _tag_source(fn: Callable, source: str) -> Callable:
        """Attach a ``_source`` attribute so the lambda can be serialized back to Python."""
        fn._source = source  # type: ignore[attr-defined]
        return fn

    @staticmethod
    def provinces_left(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda s, _me, _amount=amount, _cmp=cmp: _cmp(s.supply.get("Province", 0), _amount)
        return PriorityRule._tag_source(fn, f"PriorityRule.provinces_left({op!r}, {amount!r})")

    @staticmethod
    def turn_number(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda s, _me, _amount=amount, _cmp=cmp: _cmp(s.turn_number, _amount)
        return PriorityRule._tag_source(fn, f"PriorityRule.turn_number({op!r}, {amount!r})")

    @staticmethod
    def resources(res: str, op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        cmp = PriorityRule._OP_MAP[op]

        def _get(me, res_name: str):
            if res_name == "hand_size":
                return len(me.hand)
            return getattr(me, res_name)

        fn = lambda s, me, _amount=amount, _cmp=cmp, _res=res: _cmp(_get(me, _res), _amount)
        return PriorityRule._tag_source(fn, f"PriorityRule.resources({res!r}, {op!r}, {amount!r})")

    @staticmethod
    def has_cards(cards: Iterable[str], amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        card_list = list(cards)
        fn = lambda _s, me, _amount=amount, _cards=card_list: sum(me.count_in_deck(c) for c in _cards) >= _amount
        return PriorityRule._tag_source(fn, f"PriorityRule.has_cards({card_list!r}, {amount!r})")

    @staticmethod
    def max_in_deck(card_name: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the player has strictly fewer than ``amount`` copies of ``card_name``."""
        fn = lambda _s, me, _amount=amount, _card=card_name: me.count_in_deck(_card) < _amount
        return PriorityRule._tag_source(fn, f"PriorityRule.max_in_deck({card_name!r}, {amount!r})")

    @staticmethod
    def actions_in_play(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the number of action cards in play satisfies the comparison."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda _s, me, _amount=amount, _cmp=cmp: _cmp(
            sum(1 for c in me.in_play if c.is_action), _amount
        )
        return PriorityRule._tag_source(fn, f"PriorityRule.actions_in_play({op!r}, {amount!r})")

    @staticmethod
    def always_true() -> Callable[["GameState", "PlayerState"], bool]:
        fn = lambda *_: True
        return PriorityRule._tag_source(fn, "PriorityRule.always_true()")

    # Logical combinators -------------------------------------------------
    @staticmethod
    def and_(*conds: Optional[Callable[["GameState", "PlayerState"], bool]]):
        conds = [c for c in conds if c]

        if not conds:
            return PriorityRule.always_true()

        fn = lambda s, me: all(c(s, me) for c in conds)
        sources = ", ".join(getattr(c, "_source", "None") for c in conds)
        return PriorityRule._tag_source(fn, f"PriorityRule.and_({sources})")

    @staticmethod
    def or_(*conds: Optional[Callable[["GameState", "PlayerState"], bool]]):
        conds = [c for c in conds if c]

        if not conds:
            return PriorityRule.always_true()

        fn = lambda s, me: any(c(s, me) for c in conds)
        sources = ", ".join(getattr(c, "_source", "None") for c in conds)
        return PriorityRule._tag_source(fn, f"PriorityRule.or_({sources})")


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
    def _choose_from_priority(
        self, priority: list[PriorityRule], choices: list[Card], state: GameState, player: PlayerState
    ) -> Optional[Card]:
        """Return the first card whose rule condition evaluates to True.

        The rule condition may be one of the following:
        1. ``None`` – always true
        2. A ``Callable[[GameState, PlayerState], bool]`` – evaluated directly
        3. A legacy ``str`` expression – evaluated via the internal DSL parser
        """

        for rule in priority:
            for card in choices:
                if card is None or card.name != rule.card:
                    continue

                cond = rule.condition
                passes: bool

                if cond is None:
                    passes = True
                elif callable(cond):
                    try:
                        passes = bool(cond(state, player))
                    except Exception:
                        passes = False
                else:
                    # Legacy string conditions are no longer supported
                    passes = False

                if passes:
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
            PriorityRule.and_(PriorityRule.turn_number("<", 15), PriorityRule.has_cards(["Witch"], 0)),
        ),
        PriorityRule(
            "Chapel",
            PriorityRule.and_(PriorityRule.turn_number("<=", 4), PriorityRule.has_cards(["Chapel"], 0)),
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
