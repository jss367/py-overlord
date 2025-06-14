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
            PriorityRule("Province", "my.coins >= 8"),
            PriorityRule("Chapel", "state.turn_number <= 2 AND my.count(Chapel) == 0"),
            PriorityRule("Wharf", "my.count(Wharf) < 2"),
            PriorityRule("Village", "my.count(Bridge) + my.count(Wharf) > my.count(Village)"),
            PriorityRule("Bridge", "my.coins >= 4"),
            PriorityRule("Gold", "my.coins >= 6"),
            PriorityRule("Silver", "my.coins >= 3"),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule("Chapel", "my.count(Estate) > 0 OR my.count(Copper) > 3"),
            PriorityRule("Wharf"),
            PriorityRule("Bridge"),
            PriorityRule("Village"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", "state.turn_number <= 12"),
            PriorityRule("Copper", "my.count(Silver) + my.count(Gold) >= 2"),
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
