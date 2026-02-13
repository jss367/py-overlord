from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class EvolvedEvolvedsiegeenginev3(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen42-13590381328'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Gold'),
            PriorityRule('Catapult'),
            PriorityRule('Silver'),
            PriorityRule('Torturer', PriorityRule.turn_number('<=', 14)),
            PriorityRule('Copper', PriorityRule.provinces_left('<=', 7)),
            PriorityRule('Plunder', PriorityRule.has_cards(['Duchy', 'Silver', 'Copper'], 2)),
            PriorityRule('Highway'),
            PriorityRule('Torturer'),
            PriorityRule('Rocks', PriorityRule.turn_number('<=', 9)),
            PriorityRule('First Mate'),
        ]

        self.action_priority = [
            PriorityRule('Catapult'),
            PriorityRule('Hunting Lodge'),
            PriorityRule('Procession'),
            PriorityRule('Torturer'),
            PriorityRule('Highway', PriorityRule.provinces_left('<=', 4)),
            PriorityRule('Plunder'),
            PriorityRule('Highway'),
        ]

        self.treasure_priority = [
            PriorityRule('Silver'),
            PriorityRule('Gold'),
            PriorityRule('Copper'),
            PriorityRule('Rocks'),
            PriorityRule('Plunder'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 4)),
            PriorityRule('Rocks'),
        ]

def create_evolvedevolvedsiegeenginev3() -> EnhancedStrategy:
    return EvolvedEvolvedsiegeenginev3()