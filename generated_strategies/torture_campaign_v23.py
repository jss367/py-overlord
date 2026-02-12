from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TortureCampaignV23(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'torture-campaign-v23'
        self.description = "Hand-tuned Province rush with early Torturer attack and Patrol draw"
        self.version = "2.3"

        self.gain_priority = [
            # Province always #1
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 3)),
            # Torturer EARLY — 3 max, on 5-coin turns before Patrol
            PriorityRule(
                'Torturer',
                PriorityRule.and_(
                    PriorityRule.max_in_deck('Torturer', 3),
                    PriorityRule.turn_number('<=', 10),
                ),
            ),
            # Patrol takes over for late-game draw + VP sorting
            PriorityRule('Patrol'),
            PriorityRule('Gold'),
            PriorityRule('Emporium'),
            PriorityRule('Silver'),
            PriorityRule('Patrician'),
            PriorityRule('Taskmaster'),
        ]

        self.action_priority = [
            PriorityRule('Patrician'),
            PriorityRule('Emporium'),
            PriorityRule('Torturer', PriorityRule.resources('actions', '>', 1)),
            PriorityRule('Inn'),
            PriorityRule('Patrol'),
            PriorityRule('Torturer'),
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


def create_torture_campaign_v23() -> EnhancedStrategy:
    return TortureCampaignV23()
