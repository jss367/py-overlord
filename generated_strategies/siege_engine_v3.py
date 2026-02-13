"""Catapult/Sacrifice Trasher - Aggressive thinning + attack.

Core idea: Thin aggressively with Sacrifice and Catapult, gain Rocks for Silver,
lean deck hits Province money fast. Catapult attacks force opponents to discard.
Plunder for Gold gaining and VP.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class SiegeEngineV3(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'siege-engine-v3-trasher'
        self.description = "Catapult/Sacrifice trash-thin rush with Plunder economy"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 3)),
            # Sacrifice early for thinning (trash Estate = +2 VP tokens, trash Copper = +2 coins)
            PriorityRule('Sacrifice', PriorityRule.and_(
                PriorityRule.max_in_deck('Sacrifice', 2),
                PriorityRule.turn_number('<=', 6),
            )),
            # Catapult for trashing + attack (cheap at 3)
            PriorityRule('Catapult', PriorityRule.and_(
                PriorityRule.max_in_deck('Catapult', 2),
                PriorityRule.turn_number('<=', 8),
            )),
            # Plunder for economy — gains Gold and gives +2 coins +1 buy
            PriorityRule('Plunder', PriorityRule.max_in_deck('Plunder', 2)),
            # Rocks gives Silver on gain and is a Treasure/Victory
            PriorityRule('Rocks', PriorityRule.max_in_deck('Rocks', 2)),
            PriorityRule('Gold'),
            # Sage for cycling through the thin deck
            PriorityRule('Sage', PriorityRule.max_in_deck('Sage', 1)),
            PriorityRule('Silver', PriorityRule.turn_number('<=', 6)),
        ]

        self.action_priority = [
            PriorityRule('Sage'),
            PriorityRule('Sacrifice', PriorityRule.or_(
                PriorityRule.has_cards(['Copper'], 1),
                PriorityRule.has_cards(['Estate'], 1),
                PriorityRule.has_cards(['Curse'], 1),
            )),
            PriorityRule('Catapult'),
        ]

        self.treasure_priority = [
            PriorityRule('Plunder'),
            PriorityRule('Rocks'),
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 2)),
            PriorityRule('Rocks'),
        ]


def create_siege_engine_v3() -> EnhancedStrategy:
    return SiegeEngineV3()
