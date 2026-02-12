from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class CustomBoardStrategy(EnhancedStrategy):
    """Strategy generated from genetic algorithm for a custom Patrician board."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "CustomBoard"
        self.description = "Evolved Patrician/Emporium engine with Forager and Snowy Village"
        self.version = "1.0"

        # Gain priorities
        self.gain_priority = [
            PriorityRule("Patrician"),
            PriorityRule("Emporium"),
            PriorityRule("Forager"),
            PriorityRule("Snowy Village", PriorityRule.turn_number("<=", 10)),
            PriorityRule("Rebuild"),
            PriorityRule("Modify"),
            PriorityRule("Collection"),
            PriorityRule("Skulk"),
            PriorityRule("Miser"),
            PriorityRule("Rats"),
            PriorityRule("Sewers", PriorityRule.turn_number("<=", 5)),
            PriorityRule("Looting"),
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule("Forager"),
            PriorityRule("Modify"),
            PriorityRule("Rebuild"),
            PriorityRule("Patrician"),
            PriorityRule("Emporium"),
            PriorityRule("Snowy Village"),
            PriorityRule("Skulk"),
            PriorityRule("Miser"),
            PriorityRule("Rats"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Rats"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
        ]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_custom_board_strategy() -> EnhancedStrategy:
    return CustomBoardStrategy()
