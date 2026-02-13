"""Torturer Engine - Attack-draw strategy.

Core idea: Torturer for draw+attack, Hunting Lodge for actions and cycling,
Sacrifice to thin the deck early. Swindler for disruption.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class SiegeEngineV1(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'siege-engine-v1-torturer'
        self.description = "Torturer draw-attack engine with Hunting Lodge support"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 3)),
            # Sacrifice early for deck thinning
            PriorityRule('Sacrifice', PriorityRule.and_(
                PriorityRule.max_in_deck('Sacrifice', 1),
                PriorityRule.turn_number('<=', 4),
            )),
            # Torturer is the core engine piece
            PriorityRule('Torturer', PriorityRule.max_in_deck('Torturer', 3)),
            # Hunting Lodge for actions and draw cycling
            PriorityRule('Hunting Lodge', PriorityRule.max_in_deck('Hunting Lodge', 2)),
            # Swindler for early disruption
            PriorityRule('Swindler', PriorityRule.and_(
                PriorityRule.max_in_deck('Swindler', 1),
                PriorityRule.turn_number('<=', 8),
            )),
            PriorityRule('Gold'),
            PriorityRule('Silver', PriorityRule.turn_number('<=', 8)),
        ]

        self.action_priority = [
            PriorityRule('Sacrifice', PriorityRule.or_(
                PriorityRule.has_cards(['Copper'], 1),
                PriorityRule.has_cards(['Estate'], 1),
            )),
            PriorityRule('Hunting Lodge'),
            PriorityRule('Swindler'),
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
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 2)),
        ]


def create_siege_engine_v1() -> EnhancedStrategy:
    return SiegeEngineV1()
