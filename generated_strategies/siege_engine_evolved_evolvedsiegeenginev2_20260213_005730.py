from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class EvolvedEvolvedsiegeenginev2(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen121-13556720400'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Gold'),
            PriorityRule('Catapult', PriorityRule.turn_number('<=', 12)),
            PriorityRule('Silver'),
            PriorityRule('First Mate'),
            PriorityRule('Rocks'),
            PriorityRule('Swindler'),
            PriorityRule('Plunder'),
            PriorityRule('Highway'),
            PriorityRule('Sage', PriorityRule.has_cards(['Silver', 'Duchy', 'Estate'], 1)),
        ]

        self.action_priority = [
            PriorityRule('Highway'),
            PriorityRule('Rocks', PriorityRule.has_cards(['Duchy', 'Silver', 'Gold'], 2)),
            PriorityRule('Sage'),
            PriorityRule('Catapult'),
            PriorityRule('Swindler', PriorityRule.turn_number('<=', 18)),
            PriorityRule('Encampment'),
            PriorityRule('Torturer'),
            PriorityRule('Procession', PriorityRule.resources('actions', '>=', 6)),
            PriorityRule('Procession', PriorityRule.resources('buys', '>=', 2)),
            PriorityRule('Swindler'),
            PriorityRule('Plunder', PriorityRule.turn_number('<', 13)),
            PriorityRule('Procession'),
            PriorityRule('Plunder'),
        ]

        self.treasure_priority = [
            PriorityRule('Copper'),
            PriorityRule('Silver'),
            PriorityRule('Gold'),
            PriorityRule('Plunder'),
            PriorityRule('Rocks'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_evolvedevolvedsiegeenginev2() -> EnhancedStrategy:
    return EvolvedEvolvedsiegeenginev2()