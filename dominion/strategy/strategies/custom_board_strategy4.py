from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class CustomBoardStrategy4(EnhancedStrategy):
    """User-defined strategy for Patrician/Emporium board with Collection focus."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "CustomBoard4"
        self.description = "Collection-focused strategy with careful timing"
        self.version = "4.0"

        # Gain priorities
        self.gain_priority = [
            # Province only after getting 4 loots
            PriorityRule("Province", PriorityRule.and_("my.coins >= 8", "my.count(Looting) >= 4")),
            # Early Collection priority
            PriorityRule("Collection", PriorityRule.and_("my.coins >= 5", "my.count(Collection) == 0")),
            # Looting at 6 coins
            PriorityRule("Looting"),
            # When Collection is in play, buy small actions with remaining money
            PriorityRule("Patrician", "my.count(Collection) > 0"),
            PriorityRule("Forager", "my.count(Collection) > 0"),
            # Patrician with 2 coins when provinces > 2
            PriorityRule("Patrician", PriorityRule.and_(PriorityRule.provinces_left(">", 2), "my.coins == 2")),
            # Skulk at 4 coins (to trash with Forager)
            PriorityRule("Skulk"),
            # Get two Foragers, especially if bought Skulk
            PriorityRule("Forager", "my.count(Forager) < 2"),
            PriorityRule("Forager", "my.count(Skulk) > 0 and my.count(Forager) < 2"),
            # Silver at 3 coins if already have one Forager
            PriorityRule("Silver", "my.count(Forager) >= 1"),
            PriorityRule("Emporium"),
            # Late game victory
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            # Basic treasures
            PriorityRule("Silver"),
        ]

        # Action priorities - +1 card +1 action cards first
        self.action_priority = [
            PriorityRule("Patrician"),  # +1 card +1 action first
            PriorityRule("Forager"),
            PriorityRule("Emporium"),
            PriorityRule("Looting"),
            PriorityRule("Skulk"),
            PriorityRule("Snowy Village"),
        ]

        # Trash priorities - shelters first
        self.trash_priority = [
            PriorityRule("Overgrown Estate"),  # Top priority
            PriorityRule("Curse"),
            PriorityRule("Hovel"),
            PriorityRule("Necropolis"),
            PriorityRule("Skulk"),  # Trash Skulk with Forager
            PriorityRule("Estate"),
            PriorityRule("Copper"),
        ]

        # Treasure play order (Coppers first for Collection)
        self.treasure_priority = [
            PriorityRule("Collection"),
            PriorityRule("Copper"),
            PriorityRule("Silver"),
            PriorityRule("Gold"),
        ]


def create_custom_board_strategy4() -> EnhancedStrategy:
    return CustomBoardStrategy4()
