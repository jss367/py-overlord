from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TorturerEngine(EnhancedStrategy):
    """Engine strategy focused on Torturer, Inn, Snowy Village, and Patrol."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "TorturerEngine2"
        self.description = "Engine strategy with Torturer attack and Trail defense"
        self.version = "2.1"

        # Gain priorities
        self.gain_priority = [
            # Provinces – begin at 8 coins once the game is underway
            PriorityRule(
                "Province",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 8),
                    PriorityRule.or_(PriorityRule.provinces_left("<=", 6), PriorityRule.turn_number(">=", 12)),
                ),
            ),
            # Engine cards – keep Torturers roughly equal to total village effects
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer")
                    < me.count_in_deck("Snowy Village") + me.count_in_deck("Inn") + me.count_in_deck("Acting Troupe"),
                ),
            ),
            PriorityRule(
                "Inn",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Inn") == 0,
                ),
            ),
            PriorityRule(
                "Snowy Village",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    lambda _s, me: me.count_in_deck("Snowy Village") < 3,
                ),
            ),
            PriorityRule(
                "Patrol",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Patrol") < 2,
                ),
            ),
            # Trails for defense against Torturer – aim for up to two copies
            PriorityRule(
                "Trail",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    lambda _s, me: me.count_in_deck("Trail") < 2,
                ),
            ),
            # Taskmaster to play multiple Torturers
            PriorityRule(
                "Taskmaster",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") >= 1,
                    lambda _s, me: me.count_in_deck("Taskmaster") < 2,
                ),
            ),
            # Emporium for bonus points when we have long action chains
            PriorityRule(
                "Emporium",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Snowy Village") >= 2,
                ),
            ),
            # Acting Troupe if we need more villages
            PriorityRule(
                "Acting Troupe",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 3),
                    lambda _s, me: me.count_in_deck("Snowy Village") < 2,
                    lambda _s, me: me.count_in_deck("Acting Troupe") == 0,
                ),
            ),
            # Patrician at exactly 2 coins
            PriorityRule("Patrician", PriorityRule.resources("coins", "==", 2)),
            # Additional engine support
            PriorityRule("Snowy Village", PriorityRule.resources("coins", ">=", 4)),  # More villages
            # Late-game victory cards
            PriorityRule(
                "Duchy",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    PriorityRule.provinces_left("<=", 2),
                ),
            ),
            PriorityRule("Estate", lambda s, _me: s.empty_piles >= 2),
            # Basic treasures
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.resources("coins", "==", 3),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
            PriorityRule(
                "Gold",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 6),
                    lambda _s, me: me.count_in_deck("Torturer") >= 2,
                ),
            ),
        ]

        # Action priorities - village effects first, then draw, then attacks
        self.action_priority = [
            PriorityRule("Acting Troupe"),  # +4 actions
            PriorityRule("Patrician"),  # +1 card +1 action
            PriorityRule(
                "Snowy Village", PriorityRule.resources("actions", "<=", 1)
            ),  # +1 card +3 actions when extra actions needed
            PriorityRule("Inn"),  # +2 cards +2 actions
            PriorityRule("Patrol"),  # +3 cards
            PriorityRule("Taskmaster"),  # Play other actions multiple times
            PriorityRule("Torturer"),  # Attack last
            PriorityRule("Emporium"),  # Treasure/Action
        ]

        # Trash priorities - get rid of junk
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Overgrown Estate"),
            PriorityRule("Hovel"),
            PriorityRule("Necropolis"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
        ]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        # Special reaction priorities
        self.reaction_priority = [
            PriorityRule("Trail"),  # Discard Trail when opponent plays attack
        ]


def create_torturer_engine() -> EnhancedStrategy:
    return TorturerEngine()
