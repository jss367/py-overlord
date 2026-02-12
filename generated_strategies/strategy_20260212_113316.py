from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_113316(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen21-6288766416'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Inn', PriorityRule.turn_number('<=', 14)),
            PriorityRule('Duchy', PriorityRule.has_cards(['Province'], 3)),
            PriorityRule('Silver', PriorityRule.resources('coins', '>=', 3)),
            PriorityRule('Silver', PriorityRule.resources('coins', '>=', 3)),
            PriorityRule('Patrol', PriorityRule.turn_number('<=', 7)),
            PriorityRule('Silver'),
            PriorityRule('Snowy Village', PriorityRule.turn_number('<=', 13)),
            PriorityRule('Emporium'),
            PriorityRule('Estate', PriorityRule.provinces_left('<=', 4)),
            PriorityRule('Estate'),
            PriorityRule('Torturer'),
            PriorityRule('Snowy Village'),
            PriorityRule('Estate'),
            PriorityRule('Torturer'),
            PriorityRule('Taskmaster'),
            PriorityRule('Taskmaster', PriorityRule.turn_number('<=', 14)),
        ]

        self.action_priority = [
            PriorityRule('Torturer'),
            PriorityRule('Taskmaster'),
            PriorityRule('Acting Troupe'),
            PriorityRule('Patrician'),
            PriorityRule('Inn'),
            PriorityRule('Trader'),
            PriorityRule('Snowy Village', PriorityRule.turn_number('>=', 14)),
            PriorityRule('Inn'),
        ]

        self.treasure_priority = [
            PriorityRule('Copper'),
            PriorityRule('Silver'),
            PriorityRule('Gold'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_strategy20260212_113316() -> EnhancedStrategy:
    return Strategy20260212_113316()