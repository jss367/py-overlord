"""Open-board Torturer hybrid.

This strategy keeps the V27 Torturer/Inn/Taskmaster/Patrol priority lists and
adds the V25 Torturer response discipline. On the full open-card + landscape
board used during June 2026 exploration, the in-memory prototype went 947-53
(94.7%) over 1,000 games against the registered strategy field at 20 games per
opponent.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class OpenBoardTorturerHybrid(EnhancedStrategy):
    """V27 priorities with V25 Torturer response discipline."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "open-board-torturer-hybrid"
        self.description = (
            "Open-board Torturer engine: V27 priorities with V25's "
            "discard-vs-Curse response discipline."
        )
        self.version = "1.0"

        self.gain_priority = [
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
            PriorityRule("Province", PriorityRule.has_cards(["Torturer"], 3)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 3)),
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Silver", 2),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
            PriorityRule("Province"),
            PriorityRule("Duchy"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Patrician", PriorityRule.turn_number("<=", 15)),
        ]

        self.action_priority = [
            PriorityRule("Patrician"),
            PriorityRule("Taskmaster"),
            PriorityRule("Torturer", PriorityRule.resources("actions", ">", 1)),
            PriorityRule("Patrol", PriorityRule.resources("actions", ">", 1)),
            PriorityRule("Inn"),
            PriorityRule("Patrol"),
            PriorityRule("Torturer"),
        ]

        self.treasure_priority = [
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


def create_open_board_torturer_hybrid() -> EnhancedStrategy:
    return OpenBoardTorturerHybrid()
