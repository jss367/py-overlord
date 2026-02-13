from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TortureCampaignV4(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'torture-campaign-v4'
        self.description = "Hand-tuned Province rush based on V4 evolved strategy"
        self.version = "4.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 3)),
            PriorityRule('Patrol', PriorityRule.max_in_deck('Patrol', 4)),
            PriorityRule('Emporium', PriorityRule.actions_in_play('>=', 5)),
            PriorityRule('Gold'),
            PriorityRule('Emporium'),
            PriorityRule('Silver'),
            PriorityRule('Patrician'),
            PriorityRule('Taskmaster'),
        ]

        self.action_priority = [
            PriorityRule('Patrician'),
            PriorityRule('Emporium'),
            PriorityRule('Inn'),
            PriorityRule('Patrol'),
            PriorityRule('Trader'),
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


def create_torture_campaign_v4() -> EnhancedStrategy:
    return TortureCampaignV4()
