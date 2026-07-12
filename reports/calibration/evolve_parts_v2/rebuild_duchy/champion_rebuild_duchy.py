from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class ChampionRebuildDuchy(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen20-5224853616'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 6)),
            PriorityRule('Gold'),
            PriorityRule('Rebuild', PriorityRule.max_in_deck('Rebuild', 6)),
            PriorityRule('Silver'),
            PriorityRule('Moat', PriorityRule.max_in_deck('Moat', 3)),
        ]

        self.action_priority = [
            PriorityRule('Cellar'),
            PriorityRule('Mine'),
            PriorityRule('Feast'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 5)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_championrebuildduchy() -> EnhancedStrategy:
    return ChampionRebuildDuchy()