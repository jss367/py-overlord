from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_125127(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen5-5879449936'
        self.description = "Evolved Big Money with Patrol, First Mate, and Acting Troupe"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Patrol', PriorityRule.turn_number('<=', 11)),
            PriorityRule('First Mate', PriorityRule.turn_number('<=', 7)),
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Acting Troupe'),
            PriorityRule('Patrician'),
            PriorityRule('Silver', PriorityRule.resources('coins', '>=', 3)),
            PriorityRule('Duchy', PriorityRule.resources('coins', '>=', 1)),
            PriorityRule('Estate'),
            PriorityRule('Duchy'),
            PriorityRule('Gold'),
            PriorityRule('Torturer'),
            PriorityRule('Torturer'),
            PriorityRule('Taskmaster'),
            PriorityRule('Taskmaster', PriorityRule.turn_number('<=', 6)),
        ]

        self.action_priority = [
            PriorityRule('Acting Troupe'),
            PriorityRule('Trader'),
            PriorityRule('Patrol'),
            PriorityRule('Inn', PriorityRule.resources('coins', '>=', 1)),
            PriorityRule('First Mate'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Copper'),
            PriorityRule('Silver'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 3)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 4)),
        ]

def create_strategy20260212_125127() -> EnhancedStrategy:
    return Strategy20260212_125127()