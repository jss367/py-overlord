from .base_strategy import BaseStrategy, PriorityRule


class WharfBridgeChapelVillageStrategy(BaseStrategy):
    """Wharf/Bridge engine with Chapel thinning and Villages for actions."""

    def __init__(self):
        super().__init__()
        self.name = "WharfBridgeChapelVillage"
        self.description = "Engine using Wharf, Bridge, Chapel and Village"
        self.version = "1.0"

        # Gain priorities
        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule(
                "Chapel",
                PriorityRule.and_(
                    PriorityRule.turn_number("<=", 2),
                    lambda _s, me: me.count_in_deck("Chapel") == 0,
                ),
            ),
            PriorityRule("Wharf", lambda _s, me: me.count_in_deck("Wharf") < 2),
            PriorityRule(
                "Village",
                lambda _s, me: me.count_in_deck("Bridge") + me.count_in_deck("Wharf") > me.count_in_deck("Village"),
            ),
            PriorityRule("Bridge", PriorityRule.resources("coins", ">=", 4)),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule("Silver", PriorityRule.resources("coins", ">=", 3)),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule(
                "Chapel",
                lambda _s, me: me.count_in_deck("Estate") > 0 or me.count_in_deck("Copper") > 3,
            ),
            PriorityRule("Wharf"),
            PriorityRule("Bridge"),
            PriorityRule("Village"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.turn_number("<=", 12)),
            PriorityRule(
                "Copper",
                lambda _s, me: me.count_in_deck("Silver") + me.count_in_deck("Gold") >= 2,
            ),
        ]

        # Treasure priorities
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


from dominion.strategy.enhanced_strategy import EnhancedStrategy


def create_wharf_bridge_chapel_village() -> EnhancedStrategy:
    return WharfBridgeChapelVillageStrategy()
