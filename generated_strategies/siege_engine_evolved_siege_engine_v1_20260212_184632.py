from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class EvolvedSiegeEngineV1(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen68-6100717968'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Gold', PriorityRule.resources('coins', '>=', 6)),
            PriorityRule('Torturer', PriorityRule.turn_number('<=', 14)),
            PriorityRule('Silver'),
            PriorityRule('Torturer'),
            PriorityRule('Gold', PriorityRule.resources('coins', '>=', 6)),
            PriorityRule('Torturer'),
            PriorityRule('Torturer'),
            PriorityRule('Torturer', PriorityRule.turn_number('<=', 7)),
            PriorityRule('Torturer'),
            PriorityRule('Swindler', PriorityRule.resources('actions', '>=', 8)),
            PriorityRule('Rocks', PriorityRule.turn_number('<=', 9)),
            PriorityRule('Rocks'),
            PriorityRule('Rocks'),
            PriorityRule('Catapult'),
            PriorityRule('Catapult'),
            PriorityRule('Catapult'),
            PriorityRule('Catapult', PriorityRule.turn_number('<=', 5)),
        ]

        self.action_priority = [
            PriorityRule('Encampment'),
            PriorityRule('Torturer', PriorityRule.turn_number('>=', 10)),
            PriorityRule('Catapult', PriorityRule.turn_number('>=', 16)),
            PriorityRule('Swindler'),
            PriorityRule('Swindler'),
            PriorityRule('Torturer'),
            PriorityRule('Encampment'),
            PriorityRule('Encampment'),
            PriorityRule('Torturer'),
            PriorityRule('Swindler', PriorityRule.provinces_left('>', 3)),
            PriorityRule('Torturer'),
            PriorityRule('Encampment', PriorityRule.turn_number('>=', 3)),
            PriorityRule('Encampment'),
            PriorityRule('Swindler'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Plunder'),
            PriorityRule('Silver'),
            PriorityRule('Rocks'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 3)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_evolvedsiegeenginev1() -> EnhancedStrategy:
    return EvolvedSiegeEngineV1()