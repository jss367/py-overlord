from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_101753(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen14-13036727824'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Torturer'),
            PriorityRule('Inn', PriorityRule.turn_number('<=', 10)),
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Patrol'),
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Province'),
            PriorityRule('Taskmaster', PriorityRule.turn_number('<=', 11)),
            PriorityRule('First Mate', PriorityRule.turn_number('<=', 13)),
            PriorityRule('Patrician', PriorityRule.turn_number('<=', 11)),
            PriorityRule('Trail', PriorityRule.turn_number('<=', 10)),
            PriorityRule('Duchy'),
            PriorityRule('Acting Troupe', PriorityRule.turn_number('<=', 8)),
            PriorityRule('Province'),
            PriorityRule('Estate'),
            PriorityRule('Taskmaster', PriorityRule.turn_number('<=', 10)),
            PriorityRule('Acting Troupe', PriorityRule.turn_number('<=', 11)),
            PriorityRule('Snowy Village', PriorityRule.turn_number('<=', 9)),
        ]

        self.action_priority = [
            PriorityRule('Acting Troupe'),
            PriorityRule('Patrol'),
            PriorityRule('Inn', PriorityRule.provinces_left('>=', 7)),
            PriorityRule('Trader'),
            PriorityRule('Taskmaster'),
            PriorityRule('Patrol'),
            PriorityRule('Patrician'),
            PriorityRule('Trail'),
            PriorityRule('Torturer'),
            PriorityRule('Emporium'),
        ]

        self.treasure_priority = [
            PriorityRule('Silver'),
            PriorityRule('Gold'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_strategy20260212_101753() -> EnhancedStrategy:
    return Strategy20260212_101753()