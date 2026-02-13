from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class EvolvedSiegeEngineV3(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen61-6100959376'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Silver', PriorityRule.resources('coins', '>=', 3)),
            PriorityRule('Encampment', PriorityRule.turn_number('<=', 12)),
            PriorityRule('Rocks'),
            PriorityRule('Rocks'),
            PriorityRule('Rocks', PriorityRule.turn_number('<=', 11)),
            PriorityRule('Copper'),
            PriorityRule('Copper', PriorityRule.provinces_left('<=', 7)),
            PriorityRule('Sacrifice', PriorityRule.turn_number('<=', 9)),
            PriorityRule('Estate'),
            PriorityRule('Province'),
            PriorityRule('Catapult'),
        ]

        self.action_priority = [
            PriorityRule('First Mate'),
            PriorityRule('Torturer', PriorityRule.turn_number('>', 15)),
            PriorityRule('Highway'),
            PriorityRule('Sage'),
            PriorityRule('Plunder', PriorityRule.resources('buys', '<', 2)),
            PriorityRule('Catapult'),
            PriorityRule('Plunder', PriorityRule.resources('buys', '<', 2)),
            PriorityRule('Rocks'),
            PriorityRule('Encampment'),
            PriorityRule('Plunder', PriorityRule.provinces_left('<=', 6)),
            PriorityRule('Torturer', PriorityRule.resources('coins', '<=', 5)),
            PriorityRule('Torturer'),
            PriorityRule('Highway'),
        ]

        self.treasure_priority = [
            PriorityRule('Copper'),
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Rocks'),
            PriorityRule('Plunder'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 4)),
            PriorityRule('Rocks'),
        ]

def create_evolvedsiegeenginev3() -> EnhancedStrategy:
    return EvolvedSiegeEngineV3()