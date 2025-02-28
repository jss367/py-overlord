from .base_strategy import BaseStrategy, PriorityRule


class VillageSmithyLabStrategy(BaseStrategy):
    """Village/Smithy/Lab engine strategy implementation"""

    def __init__(self):
        super().__init__()
        self.name = "Village/Smithy/Lab Engine"
        self.description = "Engine strategy focusing on Villages and card draw"
        self.version = "2.0"

        # Define gain priorities
        self.gain_priority = [
            PriorityRule("Chapel", "state.turn_number <= 4"),
            PriorityRule("Province", "my.coins >= 8"),
            PriorityRule("Laboratory", "state.turn_number <= 10"),
            PriorityRule("Village", "my.count(Smithy) + my.count(Laboratory) >= 2"),
            PriorityRule("Gold", "my.coins >= 6"),
            PriorityRule("Duchy", "state.provinces_left <= 4"),
            PriorityRule("Silver", "my.coins >= 3"),
            PriorityRule("Estate", "state.provinces_left <= 2"),
            PriorityRule("Copper"),
        ]

        # Define action priorities
        self.action_priority = [
            PriorityRule("Chapel", "my.count(Estate) > 0 OR my.count(Copper) > 4"),
            PriorityRule("Laboratory", "my.actions >= 1"),
            PriorityRule("Village", "my.actions < 2"),
            PriorityRule("Smithy", "my.actions >= 1"),
        ]

        # Define trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", "state.turn_number <= 10"),
            PriorityRule("Copper", "my.count(Silver) + my.count(Gold) >= 3"),
        ]

        # Define treasure priorities
        self.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
