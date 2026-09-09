"""Island seeds for the Albuquerque board (``boards/albuquerque.txt``).

Kingdom: Peasant, Chapel, Masquerade, Steward, Remake, Bridge, Wandering
Minstrel, Wharf, Cultist, King's Court. No landscapes, no Colony/Platinum.

Board texture
-------------
- Four trashers (Chapel, Masquerade, Steward, Remake) make thin decks cheap.
- Wandering Minstrel is the only village; it also sifts non-Actions off the
  top of the deck, which keeps a thin engine deck drawing live cards.
- Wharf is the draw and the +Buy: +2 Cards +1 Buy this turn and next.
- Bridge is the payload: +$1 +1 Buy and every card costs $1 less, which
  stacks. King's Court on Bridge is -$3 on every card plus three Buys.
- King's Court triples Wharf (six cards and three Buys, twice) or Bridge.
- Cultist is the only attack: +2 Cards, hands out Ruins, chains itself.
  Ruins are Actions, so Wandering Minstrel keeps them on top of the deck
  unless they are trashed.
- Peasant is a cheap +Buy/+$1 that upgrades into Soldier / Fugitive /
  Disciple (a Throne Room that also gains a copy) / Teacher.

Each seed is a distinct theory of the kingdom for the island model.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

RUINS = [
    "Abandoned Mine",
    "Ruined Library",
    "Ruined Market",
    "Ruined Village",
    "Survivors",
]

ENGINE_PARTS = ["Wharf", "Bridge", "King's Court", "Cultist", "Steward", "Masquerade"]
TERMINALS = ENGINE_PARTS + ["Chapel", "Remake", "Peasant", "Soldier"]


def _ruins_rules(condition=None) -> list[PriorityRule]:
    return [PriorityRule(name, condition) for name in RUINS]


def _money_treasures() -> list[PriorityRule]:
    return [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]


def _junk_first(*rest: PriorityRule) -> list[PriorityRule]:
    """Trash Curses and Ruins before anything else."""
    return [PriorityRule("Curse"), *_ruins_rules(), *rest]


class AlbuquerqueStrategy(EnhancedStrategy):
    """Shared decision hooks for this board.

    ``multiplier_priority`` is consulted when King's Court or Disciple asks
    which Action to replay (the engine calls ``choose_action`` outside the
    main action phase for that). The main ``action_priority`` still decides
    what to play first.
    """

    steward_mode = "cards"

    def __init__(self) -> None:
        super().__init__()
        self.multiplier_priority: list[PriorityRule] = []

    def choose_action(self, state, player, choices):
        """When King's Court or Disciple asks which Action to replay, use the
        multiplier list (another King's Court with four Actions in hand, then
        Bridge, then Wharf, and so on); the main play order still decides what
        to play first, and if nothing on the multiplier list is in hand the
        King's Court is played for no effect rather than tripling a bad card."""
        in_main_phase = getattr(state, "_choosing_main_action_phase", False)
        if self.multiplier_priority and not in_main_phase:
            pick = self._choose_from_priority(
                self.multiplier_priority, choices, state, player, "multiplier"
            )
            if pick is not None:
                return pick
        return super().choose_action(state, player, choices)

    def choose_gain(self, state, player, choices):
        """Follow the gain list, except that with two piles empty and the lead,
        drain the smallest remaining pile (never Curses) to end the game."""
        pick = super().choose_gain(state, player, choices)
        if pick is not None and pick.name == "Province":
            return pick
        ender = self._pile_out_when_ahead(state, player, choices)
        return ender if ender is not None else pick

    @staticmethod
    def _pile_out_when_ahead(state, player, choices):
        """With two piles empty and the lead, drain the smallest remaining
        pile so a dead-deck stalemate cannot run to the turn limit."""
        if getattr(state, "empty_piles", 0) < 2:
            return None
        my_vp = player.get_victory_points(state)
        if any(
            other is not player and other.get_victory_points(state) >= my_vp
            for other in state.players
        ):
            return None
        candidates = [
            c
            for c in choices
            if c is not None
            and c.name != "Curse"
            and state.supply.get(c.name, 0) > 0
            and not getattr(c, "is_event", False)
            and not getattr(c, "is_project", False)
        ]
        if not candidates:
            return None
        lowest = min(candidates, key=lambda c: (state.supply.get(c.name, 0), -c.cost.coins))
        if state.supply.get(lowest.name, 0) > 4:
            return None
        return lowest

    def choose_card_to_pass_for_masquerade(self, state, player, choices):
        """Pass a Curse, then a Ruins, then an Estate, then a Copper; failing
        those, the cheapest non-Action card in hand."""
        for name in ["Curse", *RUINS, "Estate", "Copper"]:
            for card in choices:
                if card.name == name:
                    return card
        non_actions = [c for c in choices if not c.is_action]
        pool = non_actions or choices
        return min(pool, key=lambda c: (c.cost.coins, c.name))

    def choose_steward_mode(self, state, player):
        """Trash only when two hand cards pass the trash list (Steward must
        trash two); otherwise draw (engines) or take the coins (money)."""
        wanted = [
            c for c in player.hand if self.choose_trash(state, player, [c]) is c
        ]
        if len(wanted) >= 2 and state.supply.get("Province", 0) > 3:
            return "trash"
        if self.steward_mode == "cards":
            return "cards"
        return "coins"


# ---------------------------------------------------------------------------
# Money seeds
# ---------------------------------------------------------------------------


class AlbuquerqueDoubleCultistMoney(AlbuquerqueStrategy):
    """Big Money with two Cultists; no trashing."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Double Cultist Money"
        self.description = "Big Money plus two Cultists junking the opponent."
        self.version = "1.0"
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Cultist", PriorityRule.max_in_deck("Cultist", 2)),
            PriorityRule("Gold"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Cultist"), *_ruins_rules()]
        self.trash_priority = []
        self.treasure_priority = _money_treasures()


class AlbuquerqueWharfMoney(AlbuquerqueStrategy):
    """Big Money with two Wharves."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Wharf Money"
        self.description = "Big Money plus two Wharves for draw and Buys."
        self.version = "1.0"
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Wharf", PriorityRule.max_in_deck("Wharf", 2)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Wharf"), *_ruins_rules()]
        self.trash_priority = []
        self.treasure_priority = _money_treasures()


class AlbuquerqueCultistWharfMoney(AlbuquerqueStrategy):
    """Money with two Cultists and two Wharves."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Cultist Wharf Money"
        self.description = "Big Money with two Cultists and two Wharves."
        self.version = "1.0"
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Cultist", PriorityRule.max_in_deck("Cultist", 2)),
            PriorityRule("Gold"),
            PriorityRule("Wharf", PriorityRule.max_in_deck("Wharf", 2)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Cultist"),
            PriorityRule("Wharf"),
            *_ruins_rules(),
        ]
        self.trash_priority = []
        self.treasure_priority = _money_treasures()


class AlbuquerqueMasqueradeMoney(AlbuquerqueStrategy):
    """Masquerade Big Money: one Masquerade thinning Estates and Coppers."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Masquerade Money"
        self.description = "Big Money with a Masquerade thinning junk."
        self.version = "1.0"
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Masquerade", PriorityRule.max_in_deck("Masquerade", 1)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Masquerade"), *_ruins_rules()]
        self.trash_priority = _junk_first(
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.treasure_value_in_deck(">", 9)),
        )
        self.treasure_priority = _money_treasures()


# ---------------------------------------------------------------------------
# Engine seeds
# ---------------------------------------------------------------------------


def _engine_actions(opener: str) -> list[PriorityRule]:
    """Main-phase play order: village, multiplier, draw, then the opener's
    trashing while the game is young, payload last."""
    junk_in_hand = PriorityRule.or_(
        PriorityRule.card_in_hand("Estate"),
        PriorityRule.card_in_hand("Curse"),
        *[PriorityRule.card_in_hand(name) for name in RUINS],
        PriorityRule.and_(
            PriorityRule.card_in_hand("Copper"),
            PriorityRule.treasure_value_in_deck(">", 6),
        ),
    )
    rules = [
        PriorityRule("Wandering Minstrel"),
        PriorityRule(
            "King's Court",
            PriorityRule.or_(
                *[PriorityRule.card_in_hand(name) for name in ENGINE_PARTS]
            ),
        ),
        PriorityRule("Cultist"),
        PriorityRule("Wharf"),
        PriorityRule("Masquerade"),
        PriorityRule("Steward"),
        PriorityRule("Fugitive"),
        PriorityRule("Disciple"),
    ]
    # Remake's gain is mandatory, so under a Bridge a trashed Copper turns
    # into a $2 card; only Remake while no Bridge is in play.
    no_bridge = PriorityRule.not_(PriorityRule.card_in_play("Bridge"))
    if opener in ("Chapel", "Remake"):
        cond = PriorityRule.and_(junk_in_hand, PriorityRule.provinces_left(">", 4))
        if opener == "Remake":
            cond = PriorityRule.and_(cond, no_bridge)
        rules.append(PriorityRule(opener, cond))
    rules += [
        PriorityRule("Bridge"),
        PriorityRule("Chapel", junk_in_hand),
        PriorityRule("Remake", PriorityRule.and_(junk_in_hand, no_bridge)),
        PriorityRule("Teacher"),
        PriorityRule("Soldier"),
        PriorityRule("Peasant"),
        *_ruins_rules(),
    ]
    return rules


def _multiplier_targets(first: str = "Bridge") -> list[PriorityRule]:
    order = ["Bridge", "Wharf", "Cultist", "Masquerade", "Steward", "Wandering Minstrel"]
    order.remove(first)
    return [
        PriorityRule("King's Court", PriorityRule.actions_in_hand(">=", 4)),
        PriorityRule(first),
        *[PriorityRule(name) for name in order],
    ]


def _engine_trash() -> list[PriorityRule]:
    """Junk first, Estates while the game is young, and Coppers only while
    the deck keeps an economy floor (lower once Bridges carry the payload)."""
    return _junk_first(
        PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
        PriorityRule(
            "Copper",
            PriorityRule.or_(
                PriorityRule.treasure_value_in_deck(">", 6),
                PriorityRule.and_(
                    PriorityRule.has_cards(["Bridge"], 3),
                    PriorityRule.treasure_value_in_deck(">", 3),
                ),
            ),
        ),
    )


def _engine_gains(
    opener: str,
    *,
    opener_cap: int = 1,
    opener_turn: int = 4,
    kc: int = 3,
    wharf: int = 2,
    bridge: int = 6,
    minstrel: int = 4,
    cultist: int = 0,
    gold: bool = False,
    silver: int = 1,
    duchy_at: int = 2,
    green_turn: int = 12,
) -> list[PriorityRule]:
    # Green once the engine is assembled (a King's Court and three payload
    # cards) or the clock says so; before that keep building.
    engine_built = PriorityRule.or_(
        PriorityRule.and_(
            PriorityRule.has_cards(["King's Court"], 1),
            PriorityRule.has_cards(["Bridge", "Wharf", "Cultist"], 3),
        ),
        PriorityRule.turn_number(">=", green_turn),
        PriorityRule.provinces_left("<=", 5),
    )
    rules = [
        PriorityRule("Province", engine_built),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", duchy_at)),
        PriorityRule(
            opener,
            PriorityRule.and_(
                PriorityRule.max_in_deck(opener, opener_cap),
                PriorityRule.turn_number("<=", opener_turn),
            ),
        ),
    ]
    if cultist:
        rules.append(PriorityRule("Cultist", PriorityRule.max_in_deck("Cultist", cultist)))
    rules += [
        PriorityRule(
            "King's Court",
            PriorityRule.and_(
                PriorityRule.max_in_deck("King's Court", kc),
                PriorityRule.has_cards(["Bridge", "Wharf", "Cultist"], 2),
            ),
        ),
        PriorityRule("Wharf", PriorityRule.max_in_deck("Wharf", wharf)),
    ]
    if gold:
        rules.append(PriorityRule("Gold"))
    rules += [
        PriorityRule(
            "Wandering Minstrel",
            PriorityRule.and_(
                PriorityRule.deck_group_diff(TERMINALS, ["Wandering Minstrel"], ">", 1),
                PriorityRule.max_in_deck("Wandering Minstrel", minstrel),
            ),
        ),
        PriorityRule("Bridge", PriorityRule.max_in_deck("Bridge", bridge)),
        PriorityRule("Wandering Minstrel", PriorityRule.max_in_deck("Wandering Minstrel", minstrel)),
        PriorityRule(
            "Silver",
            PriorityRule.or_(
                PriorityRule.max_in_deck("Silver", silver),
                PriorityRule.and_(
                    PriorityRule.turn_number("<=", 8),
                    PriorityRule.treasure_value_in_deck("<", 9),
                ),
            ),
        ),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
    ]
    return rules


class _BridgeEngine(AlbuquerqueStrategy):
    opener = "Chapel"
    gain_kwargs: dict = {}
    multiplier_first = "Bridge"

    def __init__(self) -> None:
        super().__init__()
        self.gain_priority = _engine_gains(self.opener, **self.gain_kwargs)
        self.action_priority = _engine_actions(self.opener)
        self.multiplier_priority = _multiplier_targets(self.multiplier_first)
        self.trash_priority = _engine_trash()
        self.treasure_priority = _money_treasures()


class AlbuquerqueChapelBridgeEngine(_BridgeEngine):
    """Chapel opener into Wandering Minstrel / Wharf / Bridge / King's Court."""

    opener = "Chapel"

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Chapel Bridge Engine"
        self.description = (
            "Chapel thins hard; Wandering Minstrel villages, two Wharves, "
            "up to six Bridges and King's Court for multi-Province turns."
        )
        self.version = "1.0"


class AlbuquerqueMasqueradeBridgeEngine(_BridgeEngine):
    """Masquerade opener into the same Bridge / King's Court core."""

    opener = "Masquerade"
    gain_kwargs = {"wharf": 2, "bridge": 6}

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Masquerade Bridge Engine"
        self.description = (
            "Masquerade opener (draws while it thins); Bridges, King's Court, "
            "Wandering Minstrel villages and two Wharves."
        )
        self.version = "1.0"


class AlbuquerqueStewardBridgeEngine(_BridgeEngine):
    """Steward opener (trash two, later +2 Cards) into the Bridge core."""

    opener = "Steward"
    gain_kwargs = {"opener_cap": 2, "opener_turn": 6}

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Steward Bridge Engine"
        self.description = (
            "Two Stewards trash early and draw later; Bridges, King's Court, "
            "Wandering Minstrels and Wharves."
        )
        self.version = "1.0"


class AlbuquerqueRemakeBridgeEngine(_BridgeEngine):
    """Remake opener (Estates become Silvers, Coppers vanish) into the core."""

    opener = "Remake"

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Remake Bridge Engine"
        self.description = (
            "Remake opener, then Wandering Minstrel, Wharf, Bridge and "
            "King's Court."
        )
        self.version = "1.0"


class AlbuquerqueCultistBridgeEngine(_BridgeEngine):
    """Chapel opener; two Cultists as draw and attack alongside Bridges."""

    opener = "Chapel"
    gain_kwargs = {"cultist": 2, "wharf": 1, "bridge": 5}
    multiplier_first = "Bridge"

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Cultist Bridge Engine"
        self.description = (
            "Chapel opener; two Cultists junk the opponent and draw; Bridges, "
            "King's Court and Wandering Minstrels."
        )
        self.version = "1.0"


class AlbuquerqueWharfEngine(_BridgeEngine):
    """Chapel opener; Wharf-heavy draw with Gold payload and King's Court on Wharf."""

    opener = "Chapel"
    gain_kwargs = {"wharf": 4, "bridge": 2, "gold": True, "silver": 2, "duchy_at": 3}
    multiplier_first = "Wharf"

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Wharf Engine"
        self.description = (
            "Chapel opener; four Wharves and Gold with Wandering Minstrel "
            "villages; King's Court triples Wharf."
        )
        self.version = "1.0"


class AlbuquerqueTravellerEngine(_BridgeEngine):
    """Chapel opener plus a Peasant that walks the Traveller line."""

    opener = "Chapel"

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Traveller Engine"
        self.description = (
            "Chapel opener with one Peasant (Soldier, Fugitive, Disciple, "
            "Teacher); otherwise the Bridge / King's Court core."
        )
        self.version = "1.0"
        self.gain_priority.insert(
            3,
            PriorityRule(
                "Peasant",
                PriorityRule.and_(
                    PriorityRule.has_no_cards(
                        ["Peasant", "Soldier", "Fugitive", "Disciple", "Teacher"]
                    ),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
        )


def create_albuquerque_double_cultist_money() -> EnhancedStrategy:
    return AlbuquerqueDoubleCultistMoney()


def create_albuquerque_wharf_money() -> EnhancedStrategy:
    return AlbuquerqueWharfMoney()


def create_albuquerque_cultist_wharf_money() -> EnhancedStrategy:
    return AlbuquerqueCultistWharfMoney()


def create_albuquerque_masquerade_money() -> EnhancedStrategy:
    return AlbuquerqueMasqueradeMoney()


def create_albuquerque_chapel_bridge_engine() -> EnhancedStrategy:
    return AlbuquerqueChapelBridgeEngine()


def create_albuquerque_masquerade_bridge_engine() -> EnhancedStrategy:
    return AlbuquerqueMasqueradeBridgeEngine()


def create_albuquerque_steward_bridge_engine() -> EnhancedStrategy:
    return AlbuquerqueStewardBridgeEngine()


def create_albuquerque_remake_bridge_engine() -> EnhancedStrategy:
    return AlbuquerqueRemakeBridgeEngine()


def create_albuquerque_cultist_bridge_engine() -> EnhancedStrategy:
    return AlbuquerqueCultistBridgeEngine()


def create_albuquerque_wharf_engine() -> EnhancedStrategy:
    return AlbuquerqueWharfEngine()


def create_albuquerque_traveller_engine() -> EnhancedStrategy:
    return AlbuquerqueTravellerEngine()
