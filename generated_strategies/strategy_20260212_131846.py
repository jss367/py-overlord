from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_131846(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen26-6275307600'
        self.description = "Evolved Patrol/Taskmaster engine with Province/Duchy greening"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Patrol', PriorityRule.turn_number('<=', 13)),
            PriorityRule('Patrol'),
            PriorityRule('Taskmaster', PriorityRule.turn_number('<=', 7)),
            PriorityRule('Duchy'),
            PriorityRule('Taskmaster'),
            PriorityRule('Taskmaster', PriorityRule.turn_number('<=', 14)),
            PriorityRule('Copper'),
            PriorityRule('Copper', PriorityRule.resources('coins', '>=', 2)),
            PriorityRule('Torturer'),
            PriorityRule('Trail', PriorityRule.turn_number('<=', 9)),
            PriorityRule('Trail', PriorityRule.turn_number('<=', 9)),
            PriorityRule('Acting Troupe'),
            PriorityRule('Acting Troupe'),
            PriorityRule('Copper', PriorityRule.provinces_left('<=', 3)),
            PriorityRule('Duchy'),
            PriorityRule('First Mate', PriorityRule.turn_number('<=', 11)),
        ]

        self.action_priority = [
            PriorityRule('Patrol'),
            PriorityRule('Inn'),
            PriorityRule('Taskmaster'),
            PriorityRule('Trail'),
            PriorityRule('Torturer'),
            PriorityRule('Acting Troupe', PriorityRule.resources('coins', '>', 5)),
            PriorityRule('Emporium', PriorityRule.provinces_left('<=', 4)),
            PriorityRule('Snowy Village'),
            PriorityRule('First Mate'),
            PriorityRule('Patrician'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 5)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 4)),
        ]

def create_strategy20260212_131846() -> EnhancedStrategy:
    return Strategy20260212_131846()