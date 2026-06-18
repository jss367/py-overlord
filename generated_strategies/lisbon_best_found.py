"""Best-found strategy for ``boards/lisbon.txt``.

Kingdom: Watchtower, Clerk, Gardens, Investment, Workers' Village, City,
Collection, Festival, Expand, Peddler — with Colony and Platinum.

This file publishes the strongest policy found in the Lisbon search as a
named generated strategy. The gain policy matches the previously generated
``Lisbon City Crusher`` because the search did not find a higher-confidence
replacement.

The plan is City-first pile pressure: empty City, take Colony whenever the
City-first rule falls through, force Clerk pressure for the second pile, then
score with Province, Duchy, and Gardens before slower engines convert.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class LisbonBestFound(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Lisbon Best Found"
        self.description = (
            "Best-found Lisbon board policy: City-first pile pressure into "
            "Colony, Clerk, and a fast green pivot."
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


def create_lisbon_best_found() -> EnhancedStrategy:
    return LisbonBestFound()
