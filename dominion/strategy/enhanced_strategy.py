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
        """True when the player has at least ``amount`` matching cards.

        ``amount=0`` is treated as "has none" rather than the mathematically
        tautological "has at least zero". Older evolved strategies commonly
        used ``has_cards(["X"], 0)`` to mean "do not have X yet"; preserving
        that intent avoids always-true rules that look strategic but fire
        unconditionally.
        """
        card_list = list(cards)
        if amount <= 0:
            fn = lambda _s, me, _cards=card_list: sum(me.count_in_deck(c) for c in _cards) == 0
        else:
            fn = lambda _s, me, _amount=amount, _cards=card_list: sum(me.count_in_deck(c) for c in _cards) >= _amount
        return PriorityRule._tag_source(fn, f"PriorityRule.has_cards({card_list!r}, {amount!r})")

    @staticmethod
    def has_no_cards(cards: Iterable[str]) -> Callable[["GameState", "PlayerState"], bool]:
        """Explicit spelling for "none of these cards are in the deck"."""
        card_list = list(cards)
        fn = lambda _s, me, _cards=card_list: sum(me.count_in_deck(c) for c in _cards) == 0
        return PriorityRule._tag_source(fn, f"PriorityRule.has_no_cards({card_list!r})")

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
    def actions_gained_this_turn(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the number of actions gained this turn satisfies the comparison.

        Useful for Cauldron-style triggers ("when this is the Nth action gained
        while X is in play"). Reads ``player.actions_gained_this_turn``, which
        is reset to 0 at the start of each of the player's turns."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda _s, me, _amount=amount, _cmp=cmp: _cmp(me.actions_gained_this_turn, _amount)
        return PriorityRule._tag_source(fn, f"PriorityRule.actions_gained_this_turn({op!r}, {amount!r})")

    @staticmethod
    def cards_gained_this_turn(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the number of cards gained this turn satisfies the comparison.

        Reads ``player.cards_gained_this_turn``, which is reset to 0 at the start
        of each of the player's turns."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda _s, me, _amount=amount, _cmp=cmp: _cmp(me.cards_gained_this_turn, _amount)
        return PriorityRule._tag_source(fn, f"PriorityRule.cards_gained_this_turn({op!r}, {amount!r})")

    @staticmethod
    def card_in_play(card_name: str) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the named card is currently in play."""
        fn = lambda _s, me, _card=card_name: any(c.name == _card for c in me.in_play)
        return PriorityRule._tag_source(fn, f"PriorityRule.card_in_play({card_name!r})")

    @staticmethod
    def card_in_hand(card_name: str) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the named card is currently in hand.

        Useful for synergy rules such as "play Village only if a terminal is in
        hand", e.g. ``and_(card_in_hand("Smithy"), resources("actions", "<", 2))``.
        """
        fn = lambda _s, me, _card=card_name: any(c.name == _card for c in me.hand)
        return PriorityRule._tag_source(fn, f"PriorityRule.card_in_hand({card_name!r})")

    @staticmethod
    def actions_in_hand(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the number of action cards currently in hand satisfies the comparison."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda _s, me, _amount=amount, _cmp=cmp: _cmp(
            sum(1 for c in me.hand if c.is_action), _amount
        )
        return PriorityRule._tag_source(fn, f"PriorityRule.actions_in_hand({op!r}, {amount!r})")

    @staticmethod
    def terminals_in_hand(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the number of terminal action cards in hand satisfies the comparison.

        A terminal is an action that grants no ``+Action`` (``stats.actions == 0``)."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda _s, me, _amount=amount, _cmp=cmp: _cmp(
            sum(1 for c in me.hand if c.is_action and c.stats.actions == 0), _amount
        )
        return PriorityRule._tag_source(fn, f"PriorityRule.terminals_in_hand({op!r}, {amount!r})")

    @staticmethod
    def treasures_in_hand(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the number of treasure cards currently in hand satisfies the comparison."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda _s, me, _amount=amount, _cmp=cmp: _cmp(
            sum(1 for c in me.hand if c.is_treasure), _amount
        )
        return PriorityRule._tag_source(fn, f"PriorityRule.treasures_in_hand({op!r}, {amount!r})")

    @staticmethod
    def excess_actions(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when remaining actions minus terminals waiting in hand satisfies the comparison.

        ``excess_actions(">=", 1)`` answers "do I have headroom to play another terminal?"
        ``excess_actions("<", 1)`` answers "would playing another terminal strand me?"
        """
        cmp = PriorityRule._OP_MAP[op]

        def _eval(_s, me, _amount=amount, _cmp=cmp):
            terminals = sum(1 for c in me.hand if c.is_action and c.stats.actions == 0)
            return _cmp(me.actions - terminals, _amount)

        return PriorityRule._tag_source(_eval, f"PriorityRule.excess_actions({op!r}, {amount!r})")

    @staticmethod
    def deck_count_diff(card_a: str, card_b: str, op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when (count of card_a in deck) minus (count of card_b in deck) satisfies the comparison."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda _s, me, _a=card_a, _b=card_b, _amount=amount, _cmp=cmp: _cmp(
            me.count_in_deck(_a) - me.count_in_deck(_b), _amount
        )
        return PriorityRule._tag_source(fn, f"PriorityRule.deck_count_diff({card_a!r}, {card_b!r}, {op!r}, {amount!r})")

    @staticmethod
    def empty_piles(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the number of emptied supply piles satisfies the comparison."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda s, _me, _amount=amount, _cmp=cmp: _cmp(s.empty_piles, _amount)
        return PriorityRule._tag_source(fn, f"PriorityRule.empty_piles({op!r}, {amount!r})")

    @staticmethod
    def deck_size(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the player's total deck size (all zones) satisfies the comparison."""
        cmp = PriorityRule._OP_MAP[op]
        fn = lambda _s, me, _amount=amount, _cmp=cmp: _cmp(len(me.all_cards()), _amount)
        return PriorityRule._tag_source(fn, f"PriorityRule.deck_size({op!r}, {amount!r})")

    @staticmethod
    def action_density(op: str, percent: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when the percentage of action cards in the deck satisfies the comparison.
        Empty decks are treated as 0% density."""
        cmp = PriorityRule._OP_MAP[op]

        def _eval(_s, me, _amount=percent, _cmp=cmp):
            cards = me.all_cards()
            if not cards:
                return _cmp(0, _amount)
            density = sum(1 for c in cards if c.is_action) * 100 // len(cards)
            return _cmp(density, _amount)

        return PriorityRule._tag_source(_eval, f"PriorityRule.action_density({op!r}, {percent!r})")

    @staticmethod
    def score_diff(op: str, amount: int) -> Callable[["GameState", "PlayerState"], bool]:
        """True when (my VP - max opponent VP) satisfies the comparison.
        Useful for endgame decisions (e.g. trigger pile-out when ahead)."""
        cmp = PriorityRule._OP_MAP[op]

        def _eval(s, me, _amount=amount, _cmp=cmp):
            my_vp = me.get_victory_points(s)
            opp_vps = [
                p.get_victory_points(s) for p in s.players if p is not me
            ]
            opp_best = max(opp_vps) if opp_vps else 0
            return _cmp(my_vp - opp_best, _amount)

        return PriorityRule._tag_source(_eval, f"PriorityRule.score_diff({op!r}, {amount!r})")

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


@dataclass
class WayRule:
    """A rule selecting a Way to use when playing a particular card.

    When the engine asks ``choose_way`` for ``card``, the strategy walks
    ``way_policy`` in order and picks the first rule whose ``card_name``
    matches the played card, whose ``condition`` (if any) passes, and whose
    ``way_name`` is in the list of available Ways for the kingdom.
    """

    card_name: str
    way_name: str
    condition: Optional[Callable[["GameState", "PlayerState"], bool]] = None


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
        self.way_policy: list[WayRule] = []
        self._decision_trace_callback = None

    # ------------------------------------------------------------------
    def _choose_from_priority(
        self,
        priority: list[PriorityRule],
        choices: list[Optional[Card]],
        state: GameState,
        player: PlayerState,
        list_name: str = "priority",
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
                    # Mark the rule as having fired at least once. The
                    # ``rule_pruning`` module uses this signal during GA
                    # evolution to drop rules that never affect a buy/play
                    # decision across an entire fitness-eval window.
                    rule._fired = True
                    callback = getattr(self, "_decision_trace_callback", None)
                    if callback is not None:
                        try:
                            callback(list_name, rule, card, state, player)
                        except Exception:
                            pass
                    return card

        return None

    # ------------------------------------------------------------------
    def choose_action(self, state, player, choices):
        # Handle Trail reaction trigger: if Trail is the only real option
        # (on-gain/on-discard/on-trash reaction) and butterfly trick is
        # available, always play it so the Way fires.
        real = [c for c in choices if c is not None]
        if (len(real) == 1 and real[0].name == "Trail"
                and self._can_butterfly(state)
                and self._best_butterfly_target(state, player, real[0].cost.coins + 1)):
            return real[0]
        result = self._choose_from_priority(self.action_priority, choices, state, player, "action")
        if result is not None:
            return result

        if any(card is None for card in choices):
            return None

        # Fallback: play unexpected action cards not covered by any priority rule
        # (e.g. cards gained via Swindle or other opponent effects).
        priority_names = {rule.card for rule in self.action_priority}
        unexpected = [c for c in choices if c is not None and c.name not in priority_names]
        if not unexpected:
            return None
        return self._score_unexpected_action(unexpected, player)

    @staticmethod
    def _score_unexpected_action(unexpected: list[Card], player: PlayerState) -> Optional[Card]:
        """Pick the safest unexpected action to play.

        Prefers cantrips (+Action and +Card), then non-terminals, then terminals
        scored by net resources delivered (cards, coins, buys). A cantrip
        replaces itself in hand, so it's strictly safer than a terminal.
        """
        non_terminals = [c for c in unexpected if c.stats.actions >= 1]
        if non_terminals:
            def _nt_score(c: Card) -> tuple:
                cantrip = 1 if c.stats.cards >= 1 else 0
                return (cantrip, c.stats.actions, c.stats.cards, c.stats.coins, c.stats.buys)
            return max(non_terminals, key=_nt_score)

        # Only terminals remain. Score by net resources delivered.
        def _t_score(c: Card) -> tuple:
            return (c.stats.cards, c.stats.coins, c.stats.buys)
        return max(unexpected, key=_t_score)

    def choose_treasure(self, state, player, choices):
        result = self._choose_from_priority(self.treasure_priority, choices, state, player, "treasure")
        if result is not None:
            return result

        # Fallback: play any unexpected treasure not in our priority list
        priority_names = {rule.card for rule in self.treasure_priority}
        unexpected = [c for c in choices if c is not None and c.name not in priority_names]
        return unexpected[0] if unexpected else None

    def choose_gain(self, state, player, choices):
        normal = self._choose_from_priority(self.gain_priority, choices, state, player, "gain")
        normal = self._collection_action_gain_choice(state, player, choices, normal)

        # Trail → Butterfly trick: buy Trail at $4 to gain a $5 card
        trail = next((c for c in choices if c is not None and c.name == "Trail"), None)
        if not trail or not self._can_butterfly(state):
            return normal

        target = self._best_butterfly_target(state, player, trail.cost.coins + 1)
        if not target:
            return normal

        if normal is None:
            return trail

        # Buy Trail if the butterfly target is higher priority than normal choice
        target_idx = self._gain_priority_index(target, state, player)
        normal_idx = self._gain_priority_index(normal.name, state, player)
        if target_idx < normal_idx:
            return trail

        return normal

    def _collection_action_gain_choice(self, state, player, choices, normal):
        """Prefer useful Action gains over low-value money while Collection is active."""

        if getattr(player, "collection_played", 0) <= 0:
            return normal

        if normal is not None and normal.is_action:
            return normal

        if normal is not None and normal.name not in {"Copper", "Silver"}:
            return normal

        actions = [
            card
            for card in choices
            if card is not None
            and card.is_action
            and getattr(state, "supply", {}).get(card.name, 1) > 0
        ]
        if not actions:
            return normal

        priority_names = [rule.card_name for rule in self.gain_priority]

        def action_score(card: Card) -> tuple:
            try:
                priority = priority_names.index(card.name)
            except ValueError:
                priority = len(priority_names)
            return (
                -priority,
                card.cost.coins,
                card.stats.cards,
                card.stats.actions,
                card.stats.coins,
                card.stats.buys,
                card.name,
            )

        return max(actions, key=action_score)

    def choose_trash(self, state, player, choices):
        return self._choose_from_priority(self.trash_priority, choices, state, player, "trash")

    def choose_way(self, state, player, card, ways):
        """Choose a Way from ``way_policy`` or legacy Trail/Butterfly behavior.

        Each :class:`WayRule` matches when (a) its ``card_name`` equals the
        played card, (b) its ``condition`` (if any) passes, and (c) the named
        Way is present in ``ways``. The first matching rule wins.
        """
        policy_choice = self._choose_way_from_policy(state, player, card, ways)
        if policy_choice is not None:
            return policy_choice

        return self._choose_legacy_trail_butterfly_way(state, player, card, ways)

    def _choose_way_from_policy(self, state, player, card, ways):
        for rule in self.way_policy:
            if rule.card_name != card.name:
                continue
            cond = rule.condition
            if cond is not None:
                try:
                    if not cond(state, player):
                        continue
                except Exception:
                    continue
            for w in ways:
                if w is not None and getattr(w, "name", None) == rule.way_name:
                    return w

        return None

    def _choose_legacy_trail_butterfly_way(self, state, player, card, ways):
        """Preserve old strategies that relied on Trail using Butterfly automatically."""
        if card.name != "Trail":
            return None
        target = self._best_butterfly_target(state, player, card.cost.coins + 1)
        if not target:
            return None
        for w in ways:
            if w and getattr(w, "name", None) == "Way of the Butterfly":
                return w
        return None

    # -- Butterfly helpers -------------------------------------------------
    def _can_butterfly(self, state):
        return any(
            getattr(w, "name", None) == "Way of the Butterfly"
            for w in (getattr(state, "ways", None) or [])
        )

    def _best_butterfly_target(self, state, player, target_cost):
        """Return the name of the highest-priority card at *target_cost* that
        is in supply and whose condition passes."""
        from dominion.cards.registry import get_card
        for rule in self.gain_priority:
            if state.supply.get(rule.card, 0) <= 0:
                continue
            card_obj = get_card(rule.card)
            if card_obj is None or card_obj.cost.coins != target_cost:
                continue
            cond = rule.condition
            if cond is None or (callable(cond) and cond(state, player)):
                return rule.card
        return None

    def _gain_priority_index(self, card_name, state, player):
        """Return the index of *card_name* in gain_priority (condition passing), or inf."""
        for i, rule in enumerate(self.gain_priority):
            if rule.card != card_name:
                continue
            cond = rule.condition
            if cond is None or (callable(cond) and cond(state, player)):
                return i
        return float("inf")

    # -- Card-specific tactical defaults -----------------------------------
    def choose_watchtower_reaction(self, state, player, gained_card: Card) -> Optional[str]:
        """Default Watchtower reaction policy.

        Strategies should not have to rediscover that Watchtower trashes junk
        and topdecks newly gained engine cards. Victory cards stay in discard
        by default so they do not clog the next hand.
        """

        if gained_card.name in {"Curse", "Copper", "Ruins"}:
            return "trash"
        if gained_card.is_victory and not gained_card.is_action:
            return None
        if gained_card.is_action or gained_card.is_treasure:
            if gained_card.cost.coins >= 4:
                return "topdeck"
        return None

    def choose_card_to_topdeck_for_clerk(
        self, state, player, choices: list[Card]
    ) -> Optional[Card]:
        """Clerk attack response: put the least useful card on deck."""

        if not choices:
            return None

        def burden(card: Card) -> tuple:
            return (
                card.name not in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"},
                not (card.is_victory and not card.is_action and card.cost.coins <= 2),
                card.is_action,
                card.is_treasure,
                card.cost.coins,
                card.name,
            )

        return min(choices, key=burden)

    def should_replay_clerk(self, state, player) -> bool:
        """Backward-compatible alias for old Clerk duration strategies."""

        return True

    def should_play_clerk_reaction(self, state, player, clerk: Card | None = None) -> bool:
        """Play Clerk from hand at start of turn by default."""

        return self.should_replay_clerk(state, player)

    def choose_investment_mode(self, state, player, can_trash_treasure: bool) -> str:
        """Default Investment choice.

        Trash for VP when enough Treasure variety remains after trashing the
        weakest Treasure; otherwise take the +$1.
        """

        if not can_trash_treasure:
            return "coin"

        choices = [card for card in player.hand if getattr(card, "is_treasure", False)]
        trash = self.choose_treasure_to_trash_for_investment(state, player, choices)
        remaining_names = {
            card.name
            for card in choices
            if card is not trash and getattr(card, "is_treasure", False)
        }
        return "trash" if len(remaining_names) >= 2 else "coin"

    def choose_treasure_to_trash_for_investment(
        self, state, player, choices: list[Card]
    ) -> Optional[Card]:
        """Investment: trash the weakest Treasure from hand."""

        if not choices:
            return None
        coppers = [card for card in choices if card.name == "Copper"]
        if coppers:
            return coppers[0]
        return min(choices, key=lambda card: (card.cost.coins, card.name))


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
        PriorityRule("Laboratory", PriorityRule.always_true()),
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
