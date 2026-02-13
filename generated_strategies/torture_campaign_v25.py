from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TortureCampaignV25(EnhancedStrategy):
    """Tuned Torturer/Inn engine: 5T/4I interspersing, 3 Gold payload.

    Action math: start with 1 action, each Inn gives net +1 action.
    With 4 Inns you can play 5 Torturers.

    Interspersing rule: never buy a Torturer unless Torturers <= Inns
    (pattern: T, I, T, I, T, I, T, I, T → 5T/4I).
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "torture-campaign-v25"
        self.description = "Tuned Torturer/Inn engine: 5T/4I interspersing, 3 Gold payload"
        self.version = "2.5"

        self.gain_priority = [
            # --- Engine: strict interspersing of Torturer and Inn ---
            # Torturer only when we haven't gotten ahead of our Inn count
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Torturer", 5),
                    PriorityRule.deck_count_diff("Torturer", "Inn", "<=", 0),
                ),
            ),
            # Inn to catch up after each Torturer
            PriorityRule(
                "Inn",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Inn", 4),
                    PriorityRule.deck_count_diff("Inn", "Torturer", "<", 0),
                ),
            ),
            # Taskmaster early for +coin/+action duration support (max 2)
            PriorityRule(
                "Taskmaster",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Taskmaster", 2),
                    PriorityRule.turn_number("<=", 8),
                ),
            ),
            # Patrol for draw once engine has pieces (max 2)
            PriorityRule(
                "Patrol",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Patrol", 2),
                    PriorityRule.has_cards(["Torturer"], 2),
                ),
            ),
            # --- Greening: start once engine is online (3+ Torturers) ---
            PriorityRule("Province", PriorityRule.has_cards(["Torturer"], 3)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            # Gold payload — 3 Golds help convert engine coins into Provinces
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 3)),
            # Silver bridge for early turns
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Silver", 2),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
            # Late-game greening fallbacks
            PriorityRule("Province"),
            PriorityRule("Duchy"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 3)),
        ]

        self.action_priority = [
            # Taskmaster first — duration gives actions/coins next turn
            PriorityRule("Taskmaster"),
            # Inn BEFORE Torturer — need actions to play Torturers
            PriorityRule("Inn"),
            # Patrol when actions to spare (draw into more engine pieces)
            PriorityRule("Patrol", PriorityRule.resources("actions", ">", 1)),
            # Torturer is the payoff — play with remaining actions
            PriorityRule("Torturer"),
            # Patrol as last action
            PriorityRule("Patrol"),
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


def create_torture_campaign_v25() -> EnhancedStrategy:
    return TortureCampaignV25()
