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
            PriorityRule("Chapel", PriorityRule.turn_number("<=", 4)),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Laboratory", PriorityRule.turn_number("<=", 10)),
            PriorityRule(
                "Village",
                lambda _s, me: me.count_in_deck("Smithy") + me.count_in_deck("Laboratory") >= 2,
            ),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver", PriorityRule.resources("coins", ">=", 3)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Copper"),
        ]

        # Define action priorities
        self.action_priority = [
            PriorityRule(
                "Chapel",
                lambda _s, me: me.count_in_deck("Estate") > 0 or me.count_in_deck("Copper") > 4,
            ),
            PriorityRule("Laboratory", PriorityRule.resources("actions", ">=", 1)),
            PriorityRule("Village", PriorityRule.resources("actions", "<", 2)),
            PriorityRule("Smithy", PriorityRule.resources("actions", ">=", 1)),
        ]

        # Define trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.turn_number("<=", 10)),
            PriorityRule(
                "Copper",
                lambda _s, me: me.count_in_deck("Silver") + me.count_in_deck("Gold") >= 3,
            ),
        ]

        # Define treasure priorities
        self.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]


from dominion.strategy.enhanced_strategy import EnhancedStrategy


def create_village_smithy_lab() -> EnhancedStrategy:
    return VillageSmithyLabStrategy()
