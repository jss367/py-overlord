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
            PriorityRule("Province", PriorityRule.can_afford(8)),
            # Early trashing
            PriorityRule(
                "Chapel",
                PriorityRule.and_(PriorityRule.turn_number("<=", 2), "my.count(Chapel) == 0"),
            ),
            # Draw and actions
            PriorityRule("Laboratory", PriorityRule.can_afford(5)),
            PriorityRule("Village", PriorityRule.resources("actions", "<", 2)),
            PriorityRule("Market", PriorityRule.can_afford(5)),
            PriorityRule("Festival", PriorityRule.can_afford(5)),
            PriorityRule("Witch", PriorityRule.and_(PriorityRule.turn_number("<=", 10), "my.count(Witch) < 2")),
            # Economy
            PriorityRule("Gold", PriorityRule.can_afford(6)),
            PriorityRule("Silver", PriorityRule.can_afford(3)),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule("Chapel", "my.count(Estate) > 0 or my.count(Copper) > 2"),
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
            PriorityRule("Copper", "my.count(Silver) + my.count(Gold) >= 3"),
        ]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_ultimate_dominion() -> EnhancedStrategy:
    return UltimateDominionStrategy()
