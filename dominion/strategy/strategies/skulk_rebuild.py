from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

class SkulkRebuildStrategy(EnhancedStrategy):
    """Strategy for Forager/Skulk/Rebuild board."""

    def __init__(self):
        super().__init__()
        self.name = "SkulkRebuild"
        self.description = "Trash with Forager, gain Gold via Skulk, and score with Rebuild"
        self.version = "1.0"

        # Gain priorities
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Rebuild", "my.count(Rebuild) < 3"),
            PriorityRule("Duchy", ""),
            PriorityRule("Skulk"),
            PriorityRule("Forager", "my.count(Forager) < 1"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule("Rebuild"),
            PriorityRule("Forager"),
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

def create_skulk_rebuild() -> EnhancedStrategy:
    return SkulkRebuildStrategy()
