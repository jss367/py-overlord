from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class WizardsLichEvolved(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen15-4978269648'
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Cauldron', PriorityRule.turn_number('<=', 11)),
            PriorityRule('Province', PriorityRule.resources('coins', '>=', 8)),
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.has_cards(['Duchy', 'Province', 'Silver'], 2)),
            PriorityRule('Baker', PriorityRule.turn_number('<=', 8)),
            PriorityRule('Bustling Village'),
            PriorityRule('Mill'),
            PriorityRule('Silver'),
        ]

        self.action_priority = [
            PriorityRule('Settlers', PriorityRule.has_cards(['Province', 'Duchy', 'Gold'], 0)),
            PriorityRule('Settlers', PriorityRule.max_in_deck('Gold', 6)),
            PriorityRule('Mill', PriorityRule.score_diff('>=', -6)),
            PriorityRule('Pilgrim'),
            PriorityRule('Conjurer'),
            PriorityRule('Settlers', PriorityRule.deck_size('>', 18)),
            PriorityRule('Lurker'),
        ]

        self.treasure_priority = [
            PriorityRule('Cauldron'),
            PriorityRule('Copper'),
            PriorityRule('Gold'),
            PriorityRule('Silver'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 6)),
            PriorityRule('Hovel'),
            PriorityRule('Overgrown Estate'),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 2)),
        ]

def create_wizardslichevolved() -> EnhancedStrategy:
    return WizardsLichEvolved()