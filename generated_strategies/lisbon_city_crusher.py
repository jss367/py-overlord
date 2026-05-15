"""Counter-strategy for ``generated_strategies/lisbon_city_engine.py``.

Board: ``boards/lisbon.txt``.

The target Lisbon City Engine keeps buying payload and support after the City
pile starts to collapse. This counter leans harder into shared pile pressure:
empty City, convert to Colony when possible, keep buying Clerk to force the
second pile and topdeck attack, then score immediately with Province, Duchy,
and Gardens while the target is still carrying engine pieces.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class LisbonCityCrusher(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Lisbon City Crusher"
        self.description = (
            "City/Clerk depletion counter for the lisbon Colony board. "
            "It beats Lisbon City Engine by forcing the engine piles empty "
            "and pivoting to green before the target's payload catches up."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("City"),
            PriorityRule("Colony"),
            PriorityRule("Clerk"),
            PriorityRule("Province"),
            PriorityRule("Duchy"),
            PriorityRule("Gardens"),
            PriorityRule("Peddler"),
            PriorityRule("Silver"),
        ]

        self.action_priority = [
            PriorityRule("City"),
            PriorityRule("Watchtower"),
            PriorityRule("Peddler"),
            PriorityRule("Clerk"),
        ]

        self.treasure_priority = [
            PriorityRule("Collection"),
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Investment"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]


def create_lisbon_city_crusher() -> EnhancedStrategy:
    return LisbonCityCrusher()
