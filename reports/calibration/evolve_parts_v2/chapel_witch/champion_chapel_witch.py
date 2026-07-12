from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class ChampionChapelWitch(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen27-5423024400'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 4)),
            PriorityRule('Estate', PriorityRule.provinces_left('<=', 2)),
            PriorityRule('Gold'),
            PriorityRule('Witch', PriorityRule.max_in_deck('Witch', 3)),
            PriorityRule('Silver'),
        ]

        self.action_priority = [
            PriorityRule('Cellar'),
            PriorityRule('Moat'),
            PriorityRule('Witch'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 2)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 2)),
        ]

def create_championchapelwitch() -> EnhancedStrategy:
    return ChampionChapelWitch()