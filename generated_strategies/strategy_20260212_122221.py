from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_122221(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen5-6082219344'
        self.description = "Evolved Torturer engine with Taskmaster and Patrol draw"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Torturer'),
            PriorityRule('Taskmaster', PriorityRule.turn_number('<=', 8)),
            PriorityRule('Patrol', PriorityRule.turn_number('<=', 15)),
            PriorityRule('Duchy', PriorityRule.has_cards(['Estate', 'Province', 'Silver'], 1)),
            PriorityRule('Province'),
            PriorityRule('Estate', PriorityRule.resources('actions', '<=', 8)),
            PriorityRule('Gold'),
            PriorityRule('Trail', PriorityRule.turn_number('<=', 7)),
            PriorityRule('Acting Troupe', PriorityRule.turn_number('<=', 8)),
            PriorityRule('Emporium'),
            PriorityRule('Patrician', PriorityRule.turn_number('<=', 15)),
            PriorityRule('Inn'),
            PriorityRule('Emporium', PriorityRule.turn_number('<=', 7)),
            PriorityRule('Silver', PriorityRule.resources('coins', '>=', 3)),
            PriorityRule('Torturer', PriorityRule.turn_number('<=', 7)),
            PriorityRule('Emporium', PriorityRule.turn_number('<=', 11)),
            PriorityRule('Patrol', PriorityRule.turn_number('<=', 7)),
        ]

        self.action_priority = [
            PriorityRule('Taskmaster'),
            PriorityRule('Trader', PriorityRule.resources('coins', '>', 8)),
            PriorityRule('First Mate'),
            PriorityRule('Torturer'),
            PriorityRule('Patrol', PriorityRule.provinces_left('>', 6)),
            PriorityRule('Torturer'),
            PriorityRule('Acting Troupe'),
            PriorityRule('Taskmaster'),
            PriorityRule('Snowy Village', PriorityRule.turn_number('<=', 18)),
            PriorityRule('Trail', PriorityRule.provinces_left('>=', 5)),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_strategy20260212_122221() -> EnhancedStrategy:
    return Strategy20260212_122221()