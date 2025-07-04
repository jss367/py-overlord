from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class CustomBoardStrategy3(EnhancedStrategy):
    """Optimized strategy for Patrician/Emporium board with engine focus."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "CustomBoard3"
        self.description = "Optimized engine for Patrician/Emporium/Collection board"
        self.version = "3.0"

        # Gain priorities
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Emporium", lambda _s, me: me.count_in_deck("Snowy Village") > 0),  # Only if you can activate
            PriorityRule("Gold"),
            PriorityRule("Patrician"),
            PriorityRule("Snowy Village", lambda _s, me: me.count_in_deck("Snowy Village") < 3),
            PriorityRule("Forager", lambda _s, me: me.count_in_deck("Forager") < 2),
            PriorityRule("Collection", lambda _s, me: me.count_in_deck("Collection") < 5),
            PriorityRule("Modify", lambda _s, me: me.count_in_deck("Modify") < 2),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule("Patrician"),
            PriorityRule("Emporium"),
            PriorityRule("Forager"),
            PriorityRule("Modify"),
            PriorityRule("Snowy Village"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
            PriorityRule("Silver"),
        ]

        # Treasure play order (play Coppers before Silvers/Golds for Collection)
        self.treasure_priority = [
            PriorityRule("Copper"),
            PriorityRule("Silver"),
            PriorityRule("Gold"),
        ]


def create_custom_board_strategy3() -> EnhancedStrategy:
    return CustomBoardStrategy3()
