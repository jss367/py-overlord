from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TortureCampaignV3(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'torture-campaign-v3'
        self.description = "Hand-tuned Province rush based on V3 evolved strategy"
        self.version = "3.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 2)),
            PriorityRule('Patrol'),
            PriorityRule('Gold'),
            PriorityRule('Emporium'),
            PriorityRule('Silver'),
            PriorityRule('Patrician'),
            PriorityRule('Trail'),
            PriorityRule('First Mate'),
            PriorityRule('Taskmaster'),
            PriorityRule('Torturer'),
        ]

        self.action_priority = [
            PriorityRule('First Mate'),
            PriorityRule('Patrician'),
            PriorityRule('Emporium'),
            PriorityRule('Inn'),
            PriorityRule('Trail'),
            PriorityRule('Torturer'),
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

        self.discard_priority = [
            PriorityRule('Trail'),
        ]


def create_torture_campaign_v3() -> EnhancedStrategy:
    return TortureCampaignV3()
