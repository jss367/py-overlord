from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _engine_building_active(s, me):
    """True while curses remain in supply AND more than 4 Inn + Torturer in supply."""
    curses_remain = s.supply.get('Curse', 0) > 0
    engine_supply = s.supply.get('Inn', 0) + s.supply.get('Torturer', 0)
    return curses_remain and engine_supply > 4


class TortureCampaignV22(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'torture-campaign-v22'
        self.description = "Hand-tuned Torturer engine v22: fewer Torturers, earlier Provinces, Silver bridge"
        self.version = "2.2"

        self.gain_priority = [
            # Torturer capped at 5 (not 7) — 10 Curses don't need 7 Torturers
            PriorityRule(
                'Torturer',
                PriorityRule.and_(
                    _engine_building_active,
                    PriorityRule.max_in_deck('Torturer', 5),
                ),
            ),
            # Taskmasters for action/coin backbone
            PriorityRule(
                'Taskmaster',
                PriorityRule.and_(
                    PriorityRule.max_in_deck('Taskmaster', 4),
                    PriorityRule.turn_number('<=', 10),
                ),
            ),
            # Inn for action support (relaxed: just cap at 3)
            PriorityRule(
                'Inn',
                PriorityRule.and_(
                    _engine_building_active,
                    PriorityRule.max_in_deck('Inn', 3),
                ),
            ),
            # Province once engine has 3+ Torturers — don't wait until engine is done
            PriorityRule('Province', PriorityRule.has_cards(['Torturer'], 3)),
            # Patrol for draw consistency (max 2)
            PriorityRule('Patrol', PriorityRule.max_in_deck('Patrol', 2)),
            # One Gold for payload
            PriorityRule('Gold', PriorityRule.max_in_deck('Gold', 1)),
            # Silver bridge — prevents "nothing" turns when Taskmasters hit 3-4 coins
            PriorityRule('Silver', PriorityRule.max_in_deck('Silver', 2)),
            # Fallback greening
            PriorityRule('Province'),
            PriorityRule('Duchy'),
            PriorityRule('Estate', PriorityRule.provinces_left('<=', 4)),
        ]

        self.action_priority = [
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
