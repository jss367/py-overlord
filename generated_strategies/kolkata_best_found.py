"""Best strategy found for the Kolkata board (``boards/kolkata.txt``).

See ``reports/strategies/kolkata-strategy-guide.html`` for the search and
validation.

The hand-search leader built on the Bard Stables Money seed: two Stables
for draw, one Bard for money, one Bandit Camp for Spoils and Actions, Gold,
Silver, Duchies from four Provinces left, Estates from two. No Copper is
ever trashed (Coppers are what Stables discards). A Spoils-saving Treasure
policy was tried on this chassis and measured neutral at 1,000 games, so
the published strategy keeps the shared defaults: every Treasure is played,
and Stables discards Copper first, then Spoils, then Silver.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class KolkataBestFound(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Best Found"
        self.description = (
            "Money with two Stables, one Bard and one Bandit Camp; Gold and Silver, "
            "Duchies from four Provinces left."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Bandit Camp", PriorityRule.max_in_deck("Bandit Camp", 1)),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 2)),
            PriorityRule("Bard", PriorityRule.max_in_deck("Bard", 1)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Bandit Camp"),
            PriorityRule("Stables"),
            PriorityRule("Bard"),
        ]
        self.trash_priority = [PriorityRule("Curse"), PriorityRule("Estate")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Spoils"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_kolkata_best_found() -> EnhancedStrategy:
    return KolkataBestFound()
