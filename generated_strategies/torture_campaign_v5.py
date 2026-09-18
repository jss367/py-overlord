from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.retirement import retired_strategy


class TortureCampaignV5(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'torture-campaign-v5'
        self.description = "Hand-tuned Province rush based on V5 evolved strategy"
        self.version = "5.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule(
                'Duchy',
                PriorityRule.and_(
                    PriorityRule.provinces_left('<=', 4),
                    PriorityRule.card_in_play('Taskmaster'),
                ),
            ),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 3)),
            PriorityRule('Patrol', PriorityRule.deck_count_diff('Patrol', 'Taskmaster', '<', 3)),
            PriorityRule('Emporium', PriorityRule.actions_in_play('>=', 5)),
            PriorityRule('Emporium', PriorityRule.card_in_play('Taskmaster')),
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


@retired_strategy(
    replacement="Torture Campaign V25",
    reason="Won 22 of 1,000 confirmation games against version 25; no qualifying advantage on the tested opponent panel.",
    display_name="Torturer and Inn Family, Version 5",
)
def create_torture_campaign_v5() -> EnhancedStrategy:
    return TortureCampaignV5()
