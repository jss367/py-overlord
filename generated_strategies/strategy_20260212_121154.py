from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_121154(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen14-13115503632'
        self.description = "Evolved early-Patrol strategy with Taskmaster and First Mate support"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Patrol', PriorityRule.turn_number('<=', 11)),
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Duchy'),
            PriorityRule('Silver', PriorityRule.resources('coins', '>=', 3)),
            PriorityRule('Patrol'),
            PriorityRule('Silver'),
            PriorityRule('Patrol'),
            PriorityRule('Silver'),
            PriorityRule('Taskmaster'),
            PriorityRule('Taskmaster'),
            PriorityRule('Gold'),
            PriorityRule('Duchy', PriorityRule.resources('actions', '>=', 8)),
            PriorityRule('First Mate', PriorityRule.turn_number('<=', 6)),
            PriorityRule('Acting Troupe'),
            PriorityRule('Torturer', PriorityRule.turn_number('<=', 6)),
            PriorityRule('Estate'),
        ]

        self.action_priority = [
            PriorityRule('Inn'),
            PriorityRule('First Mate'),
            PriorityRule('Trail', PriorityRule.resources('buys', '>', 4)),
            PriorityRule('Taskmaster', PriorityRule.turn_number('>=', 15)),
            PriorityRule('First Mate'),
            PriorityRule('Inn'),
            PriorityRule('Taskmaster'),
            PriorityRule('Snowy Village'),
            PriorityRule('Acting Troupe', PriorityRule.turn_number('<', 7)),
            PriorityRule('Patrol'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Copper'),
            PriorityRule('Silver'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 2)),
        ]

def create_strategy20260212_121154() -> EnhancedStrategy:
    return Strategy20260212_121154()