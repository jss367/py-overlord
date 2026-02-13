from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TortureCampaignV27(EnhancedStrategy):
    """V25 engine with eager Torturer + Patrol before last Torturer."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "torture-campaign-v27"
        self.description = "V25 engine with eager Torturer + Patrol before last Torturer"
        self.version = "2.7"

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


def create_torture_campaign_v27() -> EnhancedStrategy:
    return TortureCampaignV27()
