from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TorturerEngine(EnhancedStrategy):
    """Engine strategy focused on Torturer, Inn, Snowy Village, and Patrol."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "TorturerEngine2"
        self.description = "Engine strategy with Torturer attack and Trail defense"
        self.version = "2.3"

        # Helper predicate for smarter village cap
        def need_more_villages(_s, me):
            terminals = me.count_in_deck("Torturer") + me.count_in_deck("Patrol") + me.count_in_deck("Inn")
            sv = me.count_in_deck("Snowy Village")
            troupe = me.count_in_deck("Acting Troupe")
            # Treat one Troupe ≈ two virtual actions banked early
            return sv + (2 * troupe) < terminals

        # Gain priorities
        self.gain_priority = [
            # Provinces normally at 8+
            PriorityRule(
                "Province",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 8),
                    lambda s, me: True,
                ),
            ),
            # Engine cards - early priorities
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") < 2,
                ),
            ),
            # Early economy smoothing: force one Silver before first $5
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 3),
                    lambda _s, me: me.count_in_deck("Silver") == 0,
                    lambda _s, me: me.count_in_deck("Torturer") == 0,
                ),
            ),
            # Early Torturer rush to 3 copies
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") < 3,
                ),
            ),
            PriorityRule(
                "Inn",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Inn") == 0,
                ),
            ),
            # Acting Troupe first; bank villagers early
            PriorityRule(
                "Acting Troupe",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 3),
                    lambda _s, me: me.count_in_deck("Acting Troupe") < 1,
                ),
            ),
            # Snowy Village only as needed to support terminals
            PriorityRule(
                "Snowy Village",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    need_more_villages,
                ),
            ),
            PriorityRule(
                "Patrol",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Patrol") < 3,
                ),
            ),
            # Trail for defense against Torturer attacks
            PriorityRule(
                "Trail",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    lambda _s, me: me.count_in_deck("Trail") < 2,
                ),
            ),
            # Taskmaster to play multiple Torturers - first one earlier, second later
            PriorityRule(
                "Taskmaster",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") >= 1,
                    lambda _s, me: me.count_in_deck("Taskmaster") < 1,
                ),
            ),
            PriorityRule(
                "Taskmaster",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") >= 2,
                    lambda _s, me: me.count_in_deck("Taskmaster") < 2,
                ),
            ),
            # Emporium for bonus points when we have long action chains
            PriorityRule(
                "Emporium",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    # Use actions played this turn as a proxy for actions in play
                    lambda s, me: me.actions_this_turn >= 5,
                ),
            ),
            # Patrician at 2 coins
            PriorityRule("Patrician", PriorityRule.resources("coins", "==", 2)),
            # Additional engine support
            PriorityRule("Torturer", PriorityRule.resources("coins", ">=", 5)),  # More Torturers if needed
            # Greening & pile control
            PriorityRule(
                "Duchy",
                PriorityRule.or_(
                    PriorityRule.provinces_left("<=", 6),
                    lambda s, _me: s.supply.get("Patrician", 0) <= 2,
                    lambda s, _me: s.supply.get("Snowy Village", 0) <= 2,
                ),
            ),
            PriorityRule(
                "Estate",
                PriorityRule.or_(
                    PriorityRule.provinces_left("<=", 3),
                    PriorityRule.and_(
                        lambda s, _me: (
                            (1 if s.supply.get("Estate", 99) <= 1 else 0)
                            + (1 if s.supply.get("Patrician", 99) <= 1 else 0)
                            + (1 if s.supply.get("Snowy Village", 99) <= 1 else 0)
                            + (1 if s.supply.get("Trail", 99) <= 1 else 0)
                        )
                        >= 2,
                        lambda _s, _me: True,
                    ),
                ),
            ),
            # Basic treasures
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
        ]

        # Action priorities - village effects first, then draw, then attacks
        self.action_priority = [
            PriorityRule("Patrician"),  # +1 card +1 action
            PriorityRule("Acting Troupe"),  # Bank villagers before doubling
            PriorityRule("Inn"),  # +2 cards +2 actions
            PriorityRule("Snowy Village"),
            PriorityRule("Taskmaster"),  # Play other actions multiple times
            PriorityRule("Patrol"),  # +3 cards
            PriorityRule("Emporium"),  # Treasure/Action
            PriorityRule("Torturer"),  # Attack last
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
