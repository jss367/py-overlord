from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _engine_building_active(s, me):
    """True while curses remain in supply AND more than 4 Inn + Torturer in supply."""
    curses_remain = s.supply.get('Curse', 0) > 0
    engine_supply = s.supply.get('Inn', 0) + s.supply.get('Torturer', 0)
    return curses_remain and engine_supply > 4

_engine_building_active._source = "_engine_building_active"


class TortureCampaignV22(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'torture-campaign-v22'
        self.description = "V21 + Inn-first then alternate Inn/Torturer balance"
        self.version = "2.2"

        self.gain_priority = [
            # Inn first for action support, then alternate with Torturer
            PriorityRule(
                'Inn',
                PriorityRule.and_(
                    _engine_building_active,
                    PriorityRule.deck_count_diff('Inn', 'Torturer', '<=', 0),
                ),
            ),
            PriorityRule(
                'Torturer',
                PriorityRule.and_(
                    _engine_building_active,
                    PriorityRule.deck_count_diff('Torturer', 'Inn', '<', 0),
                ),
            ),
            # Taskmasters fill in on cheap turns (4 coins can't buy Torturer)
            PriorityRule(
                'Taskmaster',
                PriorityRule.and_(
                    PriorityRule.max_in_deck('Taskmaster', 4),
                    PriorityRule.turn_number('<=', 10),
                ),
            ),
            # Patrol for draw consistency (max 2)
            PriorityRule('Patrol', PriorityRule.max_in_deck('Patrol', 2)),
            # One Gold for Province buying
            PriorityRule('Gold', PriorityRule.max_in_deck('Gold', 1)),
            # Greening
            PriorityRule('Province'),
            PriorityRule('Duchy'),
            PriorityRule('Estate', PriorityRule.provinces_left('<=', 4)),
            PriorityRule('Patrician', PriorityRule.turn_number('<=', 15)),
        ]

        self.action_priority = [
            PriorityRule('Patrician'),
            # Taskmasters first for +actions/+coins
            PriorityRule('Taskmaster'),
            # Torturer when multiple actions available (save last action for Inn)
            PriorityRule('Torturer', PriorityRule.resources('actions', '>', 1)),
            # Inn to generate more actions
            PriorityRule('Inn'),
            # Patrol for draw when actions to spare
            PriorityRule('Patrol', PriorityRule.resources('actions', '>', 1)),
            # Torturer as last resort
            PriorityRule('Torturer'),
            # Patrol as last resort
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


def create_torture_campaign_v22() -> EnhancedStrategy:
    return TortureCampaignV22()
