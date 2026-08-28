"""Best-found strategy for the permanently discounted Oslo Colony board.

The policy is a lean Hoard/Magnate money strategy. It deliberately skips the
slower engine components and obtains Gold from Hoard's Victory-buy trigger.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class OsloBestFound(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Oslo Best Found"
        self.description = (
            "Two-Hoard money with two Magnates, early Provinces, and a "
            "six-Provinces-left Duchy pivot."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("Hoard", PriorityRule.max_in_deck("Hoard", 2)),
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 6)),
            PriorityRule("Magnate", PriorityRule.max_in_deck("Magnate", 2)),
            PriorityRule("Silver"),
        ]

        self.action_priority = [PriorityRule("Magnate")]

        self.treasure_priority = [
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Hoard"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_oslo_best_found() -> EnhancedStrategy:
    return OsloBestFound()
