from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class RatsModifyRebuildStrategy(EnhancedStrategy):
    """Strategy utilizing Rats, Modify, Rebuild, Forager, Skulk and Patrician/Emporium."""

    def __init__(self):
        super().__init__()
        self.name = "RatsModifyRebuild"
        self.description = "Use Rats and Forager to thin, Modify for upgrades, Skulk for Gold, and Rebuild for points"
        self.version = "1.0"

        # Gain priorities
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Rebuild", "my.count(Rebuild) < 3"),
            PriorityRule("Emporium"),
            PriorityRule("Duchy"),
            PriorityRule("Patrician", "my.count(Patrician) < 2"),
            PriorityRule("Modify", "my.count(Modify) < 2"),
            PriorityRule("Skulk"),
            PriorityRule("Rats"),
            PriorityRule("Forager", "my.count(Forager) < 1"),
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
            PriorityRule("Rats"),
            PriorityRule("Patrician"),
            PriorityRule("Skulk"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
            PriorityRule("Rats"),
        ]

        # Treasure priorities
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_rats_modify_rebuild() -> EnhancedStrategy:
    return RatsModifyRebuildStrategy()
