from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class EvolvedEvolvedsiegeenginev22(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'siege-engine-evolved-v22'
        self.description = "Evolved Siege Engine v2.2"
        self.version = "2.2"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Gold'),
            PriorityRule('Catapult', PriorityRule.turn_number('<=', 12)),
            PriorityRule('Rocks'),
            PriorityRule('Silver'),
            PriorityRule('First Mate'),
            PriorityRule('Swindler'),
            PriorityRule('Plunder'),
            PriorityRule('Highway'),
            PriorityRule('Sage', PriorityRule.has_cards(['Silver', 'Duchy', 'Estate'], 1)),
        ]

        self.action_priority = [
            PriorityRule('Encampment', PriorityRule.has_cards(['Gold', 'Plunder'], 1)),
            PriorityRule('Highway'),
            PriorityRule('Sage'),
            PriorityRule('Catapult'),
            PriorityRule('Swindler', PriorityRule.turn_number('<=', 18)),
            PriorityRule('Encampment'),
            PriorityRule('Torturer'),
            PriorityRule('Procession', PriorityRule.resources('actions', '>=', 6)),
            PriorityRule('Procession', PriorityRule.resources('buys', '>=', 2)),
            PriorityRule('Swindler'),
            PriorityRule('Procession'),
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
            PriorityRule('Rocks'),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]


def create_evolvedevolvedsiegeenginev22() -> EnhancedStrategy:
    return EvolvedEvolvedsiegeenginev22()
