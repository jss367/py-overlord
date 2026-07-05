from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class ChampionGardensWorkshop(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen17-4830900016'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 6)),
            PriorityRule('Gold'),
            PriorityRule('Bureaucrat', PriorityRule.max_in_deck('Bureaucrat', 1)),
            PriorityRule('Silver', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Gardens', PriorityRule.max_in_deck('Gardens', 6)),
            PriorityRule('Moat', PriorityRule.max_in_deck('Moat', 3)),
        ]

        self.action_priority = [
            PriorityRule('Cellar'),
            PriorityRule('Moat'),
            PriorityRule('Mine'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 3)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 3)),
        ]

def create_championgardensworkshop() -> EnhancedStrategy:
    return ChampionGardensWorkshop()