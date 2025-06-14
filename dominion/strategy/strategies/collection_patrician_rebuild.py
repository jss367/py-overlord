from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class CollectionPatricianRebuildStrategy(EnhancedStrategy):
    """Strategy using Collection with Patricians plus Skulk/Forager trashing."""

    def __init__(self):
        super().__init__()
        self.name = "CollectionPatricianRebuild"
        self.description = (
            "Get Collection early then gain Patricians for VP while using Forager/Skulk"
            " for economy and trashing. Include Modify and Rebuild to close the game."
        )
        self.version = "1.0"

        # Gain priorities
        self.gain_priority = [
            PriorityRule("Province", PriorityRule.can_afford(8)),
            PriorityRule("Rebuild", "my.count(Rebuild) < 1"),
            PriorityRule("Modify", "my.count(Modify) < 1"),
            PriorityRule("Collection", "my.count(Collection) < 1"),
            PriorityRule("Forager", "my.count(Forager) < 2"),
            PriorityRule("Skulk", PriorityRule.and_(PriorityRule.can_afford(4), "my.count(Skulk) < 3")),
            PriorityRule("Patrician", "my.count(Collection) >= 1"),
            PriorityRule("Gold", PriorityRule.can_afford(6)),
            PriorityRule("Silver", PriorityRule.can_afford(3)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule("Forager"),
            PriorityRule("Modify"),
            PriorityRule("Rebuild"),
            PriorityRule("Skulk"),
            PriorityRule("Patrician"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
            PriorityRule("Skulk", "my.count(Skulk) > 2"),
            PriorityRule(
                "Gold",
                PriorityRule.and_(PriorityRule.provinces_left("<=", 2), "my.count(Modify) >= 1"),
            ),
        ]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Collection"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_collection_patrician_rebuild() -> EnhancedStrategy:
    return CollectionPatricianRebuildStrategy()
