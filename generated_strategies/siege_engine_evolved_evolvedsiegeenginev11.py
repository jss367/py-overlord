from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class EvolvedEvolvedsiegeenginev11(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'siege-engine-evolved-v11'
        self.description = "Evolved Siege Engine v1.1"
        self.version = "1.1"

        self.gain_priority = [
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Gold', PriorityRule.resources('coins', '>=', 6)),
            PriorityRule('Catapult'),
            PriorityRule('Silver'),
            PriorityRule('Gold'),
            PriorityRule('Torturer'),
            PriorityRule('Rocks'),
        ]

        self.action_priority = [
            PriorityRule('Encampment', PriorityRule.has_cards(['Gold', 'Plunder'], 1)),
            PriorityRule('Highway'),
            PriorityRule('Catapult', PriorityRule.provinces_left('>=', 2)),
            PriorityRule('Torturer'),
            PriorityRule('Catapult'),
            PriorityRule('Encampment'),
        ]

        self.treasure_priority = [
            PriorityRule('Copper'),
            PriorityRule('Rocks'),
            PriorityRule('Plunder'),
            PriorityRule('Silver'),
            PriorityRule('Gold'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 5)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 2)),
        ]


def create_evolvedevolvedsiegeenginev11() -> EnhancedStrategy:
    return EvolvedEvolvedsiegeenginev11()
