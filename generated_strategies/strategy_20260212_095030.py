from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_095030(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen5-13260322512'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Catapult'),
            PriorityRule('Astrolabe'),
            PriorityRule('Duchy'),
            PriorityRule('Cargo Ship', PriorityRule.turn_number('<=', 12)),
            PriorityRule('Copper'),
            PriorityRule('Gold'),
            PriorityRule('Catapult'),
            PriorityRule('Harbinger'),
            PriorityRule('Astrolabe'),
            PriorityRule('Treasury', PriorityRule.has_cards(['Estate', 'Silver', 'Copper'], 1)),
            PriorityRule('Duchy'),
            PriorityRule('Pickaxe'),
            PriorityRule('Trail'),
            PriorityRule('Imperial Envoy'),
            PriorityRule('Estate'),
            PriorityRule('Province'),
        ]

        self.action_priority = [
            PriorityRule('Harbinger', PriorityRule.turn_number('>=', 6)),
            PriorityRule('Joust'),
            PriorityRule('Catapult'),
            PriorityRule('Imperial Envoy', PriorityRule.turn_number('>', 16)),
            PriorityRule('Pickaxe', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Trail'),
            PriorityRule('Astrolabe'),
            PriorityRule('Imperial Envoy', PriorityRule.turn_number('>', 16)),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Copper'),
            PriorityRule('Silver'),
            PriorityRule('Pickaxe'),
            PriorityRule('Astrolabe'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 2)),
        ]

def create_strategy20260212_095030() -> EnhancedStrategy:
    return Strategy20260212_095030()