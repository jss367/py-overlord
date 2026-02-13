"""Highway Rush - Cost reduction combo.

Core idea: Stack Highways to reduce card costs, Hunting Lodge for massive draw,
buy cheap Provinces. Procession cheap cards into Highways. Sage for cycling.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class SiegeEngineV2(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'siege-engine-v2-highway'
        self.description = "Highway cost-reduction rush with Procession ladder"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 4)),
            # Highway is the core — cantrip that reduces costs
            PriorityRule('Highway', PriorityRule.max_in_deck('Highway', 4)),
            # Hunting Lodge for massive draw + actions
            PriorityRule('Hunting Lodge', PriorityRule.max_in_deck('Hunting Lodge', 2)),
            # Sage as cheap cantrip to dig past junk
            PriorityRule('Sage', PriorityRule.and_(
                PriorityRule.max_in_deck('Sage', 2),
                PriorityRule.turn_number('<=', 6),
            )),
            # Procession to upgrade Sages/Sacrifices into 5-costs
            PriorityRule('Procession', PriorityRule.and_(
                PriorityRule.max_in_deck('Procession', 2),
                PriorityRule.turn_number('<=', 10),
            )),
            PriorityRule('Gold'),
            PriorityRule('Silver', PriorityRule.turn_number('<=', 6)),
        ]

        self.action_priority = [
            PriorityRule('Highway'),
            PriorityRule('Sage'),
            PriorityRule('Hunting Lodge'),
            PriorityRule('Procession'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 2)),
        ]


def create_siege_engine_v2() -> EnhancedStrategy:
    return SiegeEngineV2()
