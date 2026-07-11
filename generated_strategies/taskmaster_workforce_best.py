from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TaskmasterWorkforceBest(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Taskmaster Workforce Best"
        self.description = "Evolved strategy for boards/taskmaster_workforce.txt"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 5)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Wharf", PriorityRule.max_in_deck("Wharf", 1)),
            PriorityRule(
                "Sculptor",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Sculptor", 1),
                    PriorityRule.provinces_left(">", 4),
                ),
            ),
            PriorityRule("Gold"),
            PriorityRule("Festival", PriorityRule.max_in_deck("Festival", 3)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 11)),
            PriorityRule("Supplies", PriorityRule.max_in_deck("Supplies", 1)),
            PriorityRule("Groom", PriorityRule.max_in_deck("Groom", 2)),
        ]

        self.action_priority = [
            PriorityRule("Lost City"),
            PriorityRule("Festival"),
            PriorityRule("Market"),
            PriorityRule("Laboratory"),
            PriorityRule("Taskmaster"),
            PriorityRule("Wharf"),
            PriorityRule("Ironworks"),
            PriorityRule("Groom"),
            PriorityRule("Sculptor"),
        ]

        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Supplies"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 2)),
        ]


def create_taskmaster_workforce_best() -> EnhancedStrategy:
    return TaskmasterWorkforceBest()
