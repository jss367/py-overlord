from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class SkulkRebuildImprovedStrategy(EnhancedStrategy):
    """Improved strategy for the Forager/Skulk/Rebuild board."""

    def __init__(self):
        super().__init__()
        self.name = "SkulkRebuildImproved"
        self.description = (
            "Enhanced Forager/Skulk/Rebuild plan with extra trashing and better late game focus"
        )
        self.version = "1.1"

        # Gain priorities
        self.gain_priority = [
            # Province when affordable
            PriorityRule("Province"),
            # Rebuild up to three copies early
            PriorityRule(
                "Rebuild",
                PriorityRule.and_(PriorityRule.provinces_left(">", 2), "my.count(Rebuild) < 3"),
            ),
            # Duchies for points
            PriorityRule("Duchy"),
            # Pick up Skulks for Gold gain
            PriorityRule("Skulk"),
            # Two Foragers to accelerate trashing
            PriorityRule("Forager", "my.count(Forager) < 2"),
            # Gain Gold if affordable
            PriorityRule("Gold"),
            # Silver only early
            PriorityRule(
                "Silver",
                PriorityRule.provinces_left(">", 3),
            ),
            # Estates once Provinces are nearly gone
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            # Use Forager early to thin the deck
            PriorityRule("Forager"),
            PriorityRule("Rebuild"),
            PriorityRule("Skulk"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
        ]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_skulk_rebuild_improved() -> EnhancedStrategy:
    return SkulkRebuildImprovedStrategy()
