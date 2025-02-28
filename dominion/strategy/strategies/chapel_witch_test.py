from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class ChapelWitchTestStrategy(EnhancedStrategy):
    """Chapel/Witch engine strategy implementation"""

    def __init__(self):
        super().__init__()
        self.name = "ChapelWitchTest"  # This is what will show up in the registry
        self.description = "Chapel/Witch engine strategy"
        self.version = "2.0"

        # Define gain priorities
        self.gain_priority = [
            PriorityRule("Province", "my.coins >= 8"),
            PriorityRule("Witch", "my.count(Witch) == 0"),
            PriorityRule("Chapel", "state.turn_number <= 5 AND my.count(Chapel) == 0"),
            PriorityRule("Gold", "my.coins >= 6"),
            PriorityRule("Silver", "my.coins >= 3"),
            PriorityRule("Copper"),
        ]

        # Define action priorities
        self.action_priority = [
            PriorityRule("Chapel", "my.count(Estate) > 0 OR my.count(Copper) > 3"),
            PriorityRule("Witch"),
        ]

        # Define trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", "state.provinces_left > 4"),
            PriorityRule("Copper", "my.count(Silver) + my.count(Gold) >= 3"),
        ]

        # Define treasure priorities
        self.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
