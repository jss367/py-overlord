from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class EvolvedEvolvedsiegeenginev1(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen67-13591588112'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

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
            PriorityRule('Highway', PriorityRule.resources('actions', '>', 3)),
            PriorityRule('Catapult', PriorityRule.provinces_left('>=', 2)),
            PriorityRule('Sage', PriorityRule.has_cards(['Estate', 'Silver', 'Copper'], 1)),
            PriorityRule('Torturer'),
            PriorityRule('Catapult'),
            PriorityRule('Swindler'),
            PriorityRule('Highway'),
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

def create_evolvedevolvedsiegeenginev1() -> EnhancedStrategy:
    return EvolvedEvolvedsiegeenginev1()