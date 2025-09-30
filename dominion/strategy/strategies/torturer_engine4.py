from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TorturerEngine(EnhancedStrategy):
    """Lean Torturer engine with early villagers (Acting Troupe), light Snowy Village, draw via Inn/Patrol, Trail defense, and real payload (Gold)."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "TorturerEngine4"
        self.description = "Optimized Torturer engine: thin/defend with Trader+Trail, bank villagers early, keep Snowy Village light, add Gold payload, then pile Provinces"
        self.version = "2.0"

        # Gain priorities (ordered top -> bottom)
        self.gain_priority = [
            # Provinces once we reliably hit 8 (no '12-coins' wait)
            PriorityRule(
                "Province",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 8),
                    lambda _s, me: me.count_in_deck("Torturer") >= 2,
                ),
            ),
            # Mid/late greening pressure
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            # Core engine pieces (early)
            PriorityRule(
                "Acting Troupe",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 3),
                    # Bank villagers early; usually 1 copy is enough, 2 if shuffle luck is poor
                    lambda _s, me: me.count_in_deck("Acting Troupe") < 2,
                ),
            ),
            PriorityRule(
                "Trader",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    # Early Trader thins Estates/Coppers and can convert incoming Curses into Silver
                    lambda _s, me: me.count_in_deck("Trader") < 1,
                ),
            ),
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") < 4,  # hit 3–4 quickly
                ),
            ),
            PriorityRule(
                "Inn",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Inn") < 2,
                ),
            ),
            PriorityRule(
                "Patrol",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Patrol") < 2,
                ),
            ),
            # Light Snowy Village: necessary sometimes, but overbuying kills your turn sequencing
            PriorityRule(
                "Snowy Village",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    lambda _s, me: me.count_in_deck("Snowy Village") < 2,
                ),
            ),
            # Trail: 1–2 copies as Torturer defense / glue
            PriorityRule(
                "Trail",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    lambda _s, me: me.count_in_deck("Trail") < 2,
                ),
            ),
            # Payload: ensure we actually hit 8+ consistently
            PriorityRule(
                "Gold",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 6),
                    lambda _s, me: me.count_in_deck("Gold") < 2,
                ),
            ),
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 3),
                    lambda _s, me: me.count_in_deck("Silver") < 2,
                ),
            ),
            # Additional Torturers after core is online
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") < 6,
                ),
            ),
            # Nice-to-haves (very low priority on this board)
            # Emporium/Taskmaster are deprioritized; they were underperformers in the log
            PriorityRule(
                "Emporium",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Emporium") < 1,
                ),
            ),
            PriorityRule(
                "Taskmaster",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Taskmaster") < 1,
                ),
            ),
        ]

        # Action priorities
        # Key idea: use villagers first (Acting Troupe), then play NORMAL villages/draw (Inn/Patrol),
        # then fire Torturers. Snowy Village last (only when safe), since it can zero-out actions in this sim.
        self.action_priority = [
            PriorityRule("Acting Troupe"),  # bank villagers first
            PriorityRule("Inn"),  # +2 Cards, +2 Actions (reliable draw/village)
            PriorityRule("Patrol"),  # +3 Cards (sifts green)
            PriorityRule("Patrician"),  # cantrip
            PriorityRule("Torturer"),  # attack/draw once actions are secured
            PriorityRule("Snowy Village"),  # LAST: only safe when you have villagers banked
            PriorityRule("Emporium"),
            PriorityRule("Taskmaster"),
        ]

        # Trash priorities (Trader handles a lot; don't trash Trail)
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
            # Keep Trail; it's defensive glue vs. Torturer
        ]

        # Treasures
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        # Reactions / on-attack behaviors
        self.reaction_priority = [
            PriorityRule("Trail"),  # Discard Trail on Torturer to cantrip/keep turn alive
            PriorityRule(
                "Trader"
            ),  # Reveal Trader on gaining Curse to take Silver instead (if engine supports this in your framework)
        ]


def create_torturer_engine() -> EnhancedStrategy:
    return TorturerEngine()
