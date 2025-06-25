from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class CollectionPatricianRebuildStrategy(EnhancedStrategy):
    """Strategy using Collection with Patricians plus Skulk/Forager trashing."""

    def __init__(self):
        super().__init__()
        self.name = "CollectionPatricianRebuild"
        self.description = (
            "Get Collection early then gain Patricians for VP while using Forager/Skulk"
            " for economy and trashing. Include Modify and Rebuild to close the game."
        )
        self.version = "1.0"

        # Gain priorities
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Rebuild", lambda _s, me: me.count_in_deck("Rebuild") < 1),
            PriorityRule("Modify", lambda _s, me: me.count_in_deck("Modify") < 1),
            PriorityRule("Collection", lambda _s, me: me.count_in_deck("Collection") < 1),
            PriorityRule("Forager", lambda _s, me: me.count_in_deck("Forager") < 2),
            PriorityRule("Skulk", lambda _s, me: me.count_in_deck("Skulk") < 3),
            PriorityRule("Patrician", lambda _s, me: me.count_in_deck("Collection") >= 1),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Copper"),
        ]

        # Action priorities
        self.action_priority = [
            PriorityRule("Forager"),
            PriorityRule("Modify"),
            PriorityRule("Rebuild"),
            PriorityRule("Skulk"),
            PriorityRule("Patrician"),
        ]

        # Trash priorities
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
            PriorityRule("Skulk", lambda _s, me: me.count_in_deck("Skulk") > 2),
            PriorityRule(
                "Gold",
                PriorityRule.and_(
                    PriorityRule.provinces_left("<=", 2),
                    lambda _s, me: me.count_in_deck("Modify") >= 1,
                ),
            ),
        ]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Collection"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_collection_patrician_rebuild() -> EnhancedStrategy:
    return CollectionPatricianRebuildStrategy()
