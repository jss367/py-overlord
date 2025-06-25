from .base_strategy import BaseStrategy, PriorityRule
from dominion.strategy.enhanced_strategy import EnhancedStrategy


class UltimateDominionStrategy(BaseStrategy):
    """Comprehensive engine strategy combining trashing, draw, and payload."""

    def __init__(self):
        super().__init__()
        self.name = "UltimateDominion"
        self.description = "Strong engine approach with Chapel trashing and powerful payload"
        self.version = "1.0"

        # Gain priorities
        self.gain_priority = [
            # Victory points
            PriorityRule("Province"),
            # Early trashing
            PriorityRule(
                "Chapel",
                PriorityRule.and_(
                    PriorityRule.turn_number("<=", 2),
                    lambda _s, me: me.count_in_deck("Chapel") == 0,
                ),
            ),
            # Draw and actions
            PriorityRule("Laboratory"),
            PriorityRule("Village", PriorityRule.resources("actions", "<", 2)),
            PriorityRule("Market"),
            PriorityRule("Festival"),
            PriorityRule(
                "Witch",
                PriorityRule.and_(
                    PriorityRule.turn_number("<=", 10),
                    lambda _s, me: me.count_in_deck("Witch") < 2,
                ),
            ),
            # Economy
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule(
                "Chapel",
                lambda _s, me: me.count_in_deck("Estate") > 0 or me.count_in_deck("Copper") > 2,
            ),
            PriorityRule("Witch"),
            PriorityRule("Village"),
            PriorityRule("Market"),
            PriorityRule("Festival"),
            PriorityRule("Laboratory"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule(
                "Copper",
                lambda _s, me: me.count_in_deck("Silver") + me.count_in_deck("Gold") >= 3,
            ),
        ]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_ultimate_dominion() -> EnhancedStrategy:
    return UltimateDominionStrategy()
