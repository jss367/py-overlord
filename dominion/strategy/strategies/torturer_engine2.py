from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TorturerEngine(EnhancedStrategy):
    """Engine strategy focused on Torturer, Inn, Snowy Village, and Patrol."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "TorturerEngine"
        self.description = "Engine strategy with Torturer attack and Trail defense"
        self.version = "2.1"

        # Gain priorities
        self.gain_priority = [
            # Provinces – begin at 8 coins once the game is underway
            PriorityRule(
                "Province",
                PriorityRule.and_(
                    "my.coins >= 8",
                    PriorityRule.or_(PriorityRule.provinces_left("<=", 6), PriorityRule.turn_number(">=", 12)),
                ),
            ),
            # Engine cards – keep Torturers roughly equal to total village effects
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    "my.coins >= 5",
                    "my.count(Torturer) < my.count(Snowy Village) + my.count(Inn) + my.count(Acting Troupe)",
                ),
            ),
            PriorityRule("Inn", PriorityRule.and_("my.coins >= 5", "my.count(Inn) == 0")),
            PriorityRule("Snowy Village", PriorityRule.and_("my.coins >= 4", "my.count(Snowy Village) < 3")),
            PriorityRule("Patrol", PriorityRule.and_("my.coins >= 5", "my.count(Patrol) < 2")),
            # Trails for defense against Torturer – aim for up to two copies
            PriorityRule("Trail", PriorityRule.and_("my.coins >= 4", "my.count(Trail) < 2")),
            # Taskmaster to play multiple Torturers
            PriorityRule(
                "Taskmaster", PriorityRule.and_("my.coins >= 5", "my.count(Torturer) >= 1", "my.count(Taskmaster) < 2")
            ),
            # Emporium for bonus points when we have long action chains
            PriorityRule("Emporium", PriorityRule.and_("my.coins >= 5", "my.count(Snowy Village) >= 2")),
            # Acting Troupe if we need more villages
            PriorityRule(
                "Acting Troupe",
                PriorityRule.and_("my.coins >= 3", "my.count(Snowy Village) < 2", "my.count(Acting Troupe) == 0"),
            ),
            # Patrician at exactly 2 coins
            PriorityRule("Patrician", "my.coins == 2"),
            # Additional engine support
            PriorityRule("Snowy Village", "my.coins >= 4"),  # More villages
            # Late-game victory cards
            PriorityRule("Duchy", PriorityRule.and_("my.coins >= 5", PriorityRule.provinces_left("<=", 2))),
            PriorityRule("Estate", "state.empty_piles >= 2"),
            # Basic treasures
            PriorityRule("Silver", PriorityRule.and_("my.coins == 3", PriorityRule.turn_number("<=", 6))),
            PriorityRule("Gold", PriorityRule.and_("my.coins >= 6", "my.count(Torturer) >= 2")),
        ]

        # Action priorities - village effects first, then draw, then attacks
        self.action_priority = [
            PriorityRule("Acting Troupe"),  # +4 actions
            PriorityRule("Patrician"),  # +1 card +1 action
            PriorityRule("Snowy Village", "my.actions <= 1"),  # +1 card +3 actions when extra actions needed
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
