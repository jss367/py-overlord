from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20260212_094841(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen8-5444101776'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Duchy'),
            PriorityRule('Catapult'),
            PriorityRule('Estate', PriorityRule.turn_number('<', 10)),
            PriorityRule('Estate'),
            PriorityRule('Silver', PriorityRule.resources('coins', '>=', 3)),
            PriorityRule('Estate', PriorityRule.resources('actions', '<', 3)),
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Gold'),
            PriorityRule('Imperial Envoy'),
            PriorityRule('Copper'),
            PriorityRule('Province'),
            PriorityRule('Gold'),
            PriorityRule('Astrolabe', PriorityRule.turn_number('<=', 11)),
            PriorityRule('Astrolabe'),
            PriorityRule('Trail', PriorityRule.turn_number('<=', 10)),
            PriorityRule('Imperial Envoy', PriorityRule.turn_number('<=', 6)),
        ]

        self.action_priority = [
            PriorityRule('Trail', PriorityRule.has_cards(['Copper', 'Estate'], 0)),
            PriorityRule('Treasury'),
            PriorityRule('Harbinger'),
            PriorityRule('Graverobber', PriorityRule.turn_number('<=', 3)),
            PriorityRule('Catapult'),
            PriorityRule('Pickaxe', PriorityRule.provinces_left('>=', 6)),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_strategy20260212_094841() -> EnhancedStrategy:
    return Strategy20260212_094841()