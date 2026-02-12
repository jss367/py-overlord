from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_111527(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen2-13425915472'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Patrol'),
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Emporium'),
            PriorityRule('Patrician'),
            PriorityRule('Trail'),
            PriorityRule('Emporium'),
            PriorityRule('Patrol'),
            PriorityRule('First Mate'),
            PriorityRule('Copper', PriorityRule.turn_number('>', 5)),
            PriorityRule('Taskmaster'),
            PriorityRule('Torturer'),
            PriorityRule('Duchy'),
        ]

        self.action_priority = [
            PriorityRule('Torturer'),
            PriorityRule('Inn', PriorityRule.has_cards(['Gold', 'Estate', 'Copper'], 4)),
            PriorityRule('Trail'),
            PriorityRule('Patrician'),
            PriorityRule('Patrol'),
            PriorityRule('Emporium'),
            PriorityRule('Trader'),
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


def create_strategy20260212_111527() -> EnhancedStrategy:
    return Strategy20260212_111527()
