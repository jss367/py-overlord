from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class EvolvedSiegeEngineV2(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen58-6100400208'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('First Mate'),
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Swindler'),
            PriorityRule('Swindler'),
            PriorityRule('Duchy', PriorityRule.resources('coins', '>', 5)),
            PriorityRule('Copper'),
            PriorityRule('Highway'),
            PriorityRule('Sacrifice'),
            PriorityRule('Sacrifice'),
            PriorityRule('Encampment', PriorityRule.turn_number('<=', 5)),
            PriorityRule('Encampment'),
            PriorityRule('Gold'),
            PriorityRule('Torturer', PriorityRule.turn_number('<=', 14)),
            PriorityRule('Torturer'),
            PriorityRule('First Mate'),
            PriorityRule('Hunting Lodge'),
            PriorityRule('Sage', PriorityRule.turn_number('<=', 12)),
            PriorityRule('Sage'),
            PriorityRule('Sage'),
            PriorityRule('Sage', PriorityRule.turn_number('<=', 14)),
        ]

        self.action_priority = [
            PriorityRule('Hunting Lodge', PriorityRule.turn_number('>=', 8)),
            PriorityRule('Rocks', PriorityRule.has_cards(['Silver', 'Copper'], 3)),
            PriorityRule('First Mate', PriorityRule.resources('coins', '<=', 7)),
            PriorityRule('Procession', PriorityRule.has_cards(['Estate', 'Gold'], 4)),
            PriorityRule('Swindler'),
            PriorityRule('First Mate', PriorityRule.has_cards(['Copper', 'Gold', 'Silver'], 1)),
            PriorityRule('Sacrifice'),
            PriorityRule('Sacrifice', PriorityRule.turn_number('<', 3)),
            PriorityRule('Swindler'),
            PriorityRule('Swindler', PriorityRule.provinces_left('<=', 2)),
            PriorityRule('Sacrifice'),
            PriorityRule('Plunder', PriorityRule.has_cards(['Duchy'], 0)),
        ]

        self.treasure_priority = [
            PriorityRule('Rocks'),
            PriorityRule('Silver'),
            PriorityRule('Gold'),
            PriorityRule('Plunder'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_evolvedsiegeenginev2() -> EnhancedStrategy:
    return EvolvedSiegeEngineV2()