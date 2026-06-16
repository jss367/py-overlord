"""GA-evolved open-board cycle strategy.

Seeded from the V25/V26/V27/Hybrid/Strategy20260212 Torturer cycle and trained
with racing, common random numbers, hall-of-fame opponents, and structured
genome mutations. In a 40-game top-panel validation after training, this
strategy finished first by aggregate record: 227-93 (70.9%), ahead of
Torture Campaign V25 at 225-95 (70.3%). V25 still had the cleaner pair record,
so this is best treated as a complementary open-board champion rather than a
strictly dominant replacement.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class OpenBoardCycleEvolved(EnhancedStrategy):
    """Open-board Torturer/Colony hybrid evolved against the cycle panel."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "open-board-cycle-evolved"
        self.description = (
            "GA-evolved open-board Torturer/Colony hybrid trained against "
            "the V25/V26/V27/hybrid cycle panel."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Torturer", 5),
                    PriorityRule.deck_count_diff("Torturer", "Inn", "<=", 0),
                ),
            ),
            PriorityRule(
                "Inn",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Inn", 4),
                    PriorityRule.deck_count_diff("Inn", "Torturer", "<", 0),
                ),
            ),
            PriorityRule(
                "Taskmaster",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Taskmaster", 2),
                    PriorityRule.turn_number("<=", 8),
                ),
            ),
            PriorityRule(
                "Patrol",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Patrol", 2),
                    PriorityRule.has_cards(["Torturer"], 2),
                ),
            ),
            PriorityRule("Platinum"),
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 4)),
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Silver", 2),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
            PriorityRule("Duchy"),
            PriorityRule("Estate", PriorityRule.colonies_left("<=", 3)),
            PriorityRule("Patrician", PriorityRule.max_in_deck("Patrician", 3)),
        ]

        self.action_priority = [
            PriorityRule("Patrician"),
            PriorityRule("Taskmaster"),
            PriorityRule("Torturer", PriorityRule.resources("actions", ">", 1)),
            PriorityRule("Patrol", PriorityRule.resources("actions", ">", 1)),
            PriorityRule("Patrol"),
            PriorityRule("Inn"),
            PriorityRule("Torturer"),
        ]

        self.treasure_priority = [
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]

    def choose_torturer_response(self, state, player):
        """Discard at 4+ cards; otherwise take the Curse to preserve hand shape."""

        return len(player.hand) >= 4


def create_open_board_cycle_evolved() -> EnhancedStrategy:
    return OpenBoardCycleEvolved()
