from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.retirement import retired_strategy


class CustomBoardStrategy2(EnhancedStrategy):
    """Strategy generated from genetic algorithm for a custom Patrician board."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "CustomBoard2"
        self.description = "Evolved Province-first Emporium/Patrician engine with Rebuild"
        self.version = "2.0"

        # Gain priorities
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Emporium"),
            PriorityRule("Patrician"),
            PriorityRule("Forager"),
            PriorityRule("Snowy Village", PriorityRule.turn_number("<=", 10)),
            PriorityRule("Rebuild"),
            PriorityRule("Modify"),
            PriorityRule("Collection"),
            PriorityRule("Skulk"),
            PriorityRule("Miser"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
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


@retired_strategy(
    replacement="Custom Board Strategy3",
    reason="Won 0 of 1,000 confirmation games with Estates and 2 of 1,000 with Shelters against the retained engine; no qualifying opponent-panel advantage.",
    display_name="Province-first Patrician and Rebuild",
)
def create_custom_board_strategy2() -> EnhancedStrategy:
    return CustomBoardStrategy2()
