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
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Witch", lambda _s, me: me.count_in_deck("Witch") == 0),
            PriorityRule(
                "Chapel",
                PriorityRule.and_(
                    PriorityRule.turn_number("<=", 5),
                    lambda _s, me: me.count_in_deck("Chapel") == 0,
                ),
            ),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule("Silver", PriorityRule.resources("coins", ">=", 3)),
            PriorityRule("Copper"),
        ]

        # Define action priorities
        self.action_priority = [
            PriorityRule(
                "Chapel",
                lambda _s, me: me.count_in_deck("Estate") > 0 or me.count_in_deck("Copper") > 3,
            ),
            PriorityRule("Witch"),
        ]

        # Define trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule(
                "Copper",
                lambda _s, me: me.count_in_deck("Silver") + me.count_in_deck("Gold") >= 3,
            ),
        ]

        # Define treasure priorities
        self.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
