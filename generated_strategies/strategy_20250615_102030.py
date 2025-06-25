from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20250615_102030(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen0-4391270256'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Village'),
            PriorityRule('Smithy'),
            PriorityRule('Market'),
            PriorityRule('Festival'),
            PriorityRule('Laboratory', PriorityRule.turn_number('<=', 7)),
            PriorityRule('Mine'),
            PriorityRule('Witch', PriorityRule.turn_number('<=', 9)),
            PriorityRule('Moat'),
            PriorityRule('Workshop'),
            PriorityRule('Chapel'),
            PriorityRule('Copper'),
            PriorityRule('Silver'),
            PriorityRule('Gold'),
            PriorityRule('Estate'),
            PriorityRule('Duchy'),
            PriorityRule('Province'),
        ]

        self.action_priority = [
            PriorityRule('Smithy'),
            PriorityRule('Market'),
            PriorityRule('Festival'),
            PriorityRule('Laboratory'),
            PriorityRule('Mine'),
            PriorityRule('Witch'),
            PriorityRule('Workshop'),
            PriorityRule('Chapel'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', lambda _s, me: me.count_in_deck('Silver') + me.count_in_deck('Gold') >= 3),
        ]

def create_strategy20250615_102030() -> EnhancedStrategy:
    return Strategy20250615_102030()