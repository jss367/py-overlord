from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class VictoriaEngine(EnhancedStrategy):
    """Charlatan engine for the Victoria board.

    Plan: thin with Sailor + Change, draw with Wayfarer, glue with Treasury,
    payload with Charlatan, double with Daimyo, claim Flag with Flag Bearer.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "VictoriaEngine"
        self.description = "Charlatan engine: Sailor thin, Wayfarer draw, Daimyo doublers"
        self.version = "1.0"

        self.gain_priority = [
            # Endgame VP
            PriorityRule("Province", PriorityRule.has_cards(["Charlatan", "Wayfarer"], 3)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),

            # One Flag Bearer for the +1 card/turn artifact
            PriorityRule("Flag Bearer", PriorityRule.max_in_deck("Flag Bearer", 1)),

            # Daimyo only after we have something worth doubling
            PriorityRule(
                "Daimyo",
                PriorityRule.and_(
                    PriorityRule.has_cards(["Charlatan", "Wayfarer"], 2),
                    PriorityRule.max_in_deck("Daimyo", 2),
                ),
            ),

            # Sack of Loot once engine is online
            PriorityRule(
                "Sack of Loot",
                PriorityRule.has_cards(["Charlatan", "Wayfarer"], 3),
            ),

            # Wayfarer is our draw
            PriorityRule("Wayfarer", PriorityRule.max_in_deck("Wayfarer", 2)),

            # Charlatan is the curser/payload — go heavy
            PriorityRule("Charlatan", PriorityRule.max_in_deck("Charlatan", 4)),

            # Treasury cantrip glue
            PriorityRule("Treasury", PriorityRule.max_in_deck("Treasury", 3)),

            # Two Sailors max (thin + duration money)
            PriorityRule("Sailor", PriorityRule.max_in_deck("Sailor", 2)),

            # One Change for an Estate→$5 upgrade
            PriorityRule(
                "Change",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Change", 1),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),

            # One Duplicate as a free $5 gainer
            PriorityRule(
                "Duplicate",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Duplicate", 1),
                    PriorityRule.has_cards(["Charlatan", "Treasury"], 1),
                ),
            ),

            # Stockpile only as opening econ
            PriorityRule(
                "Stockpile",
                PriorityRule.and_(
                    PriorityRule.turn_number("<=", 2),
                    PriorityRule.max_in_deck("Stockpile", 1),
                ),
            ),

            # Treasures fallback
            PriorityRule("Gold"),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 8)),
        ]

        self.action_priority = [
            # Cantrips first (no opportunity cost)
            PriorityRule("Treasury"),
            # Daimyo's +1 card +1 action then doubles next terminal — must come
            # before terminals so the doubled play is the strong one.
            PriorityRule("Daimyo"),
            # Sailor (+1 action) and its trash trigger next turn
            PriorityRule("Sailor"),
            # Draw before payload so we see more cards
            PriorityRule("Wayfarer", PriorityRule.resources("actions", ">=", 1)),
            # Payload
            PriorityRule("Charlatan", PriorityRule.resources("actions", ">=", 1)),
            # Trasher when we have something worth trashing
            PriorityRule(
                "Change",
                PriorityRule.and_(
                    PriorityRule.resources("actions", ">=", 1),
                    PriorityRule.or_(
                        PriorityRule.card_in_hand("Estate"),
                        PriorityRule.card_in_hand("Copper"),
                    ),
                ),
            ),
            # Flag Bearer last (terminal $2)
            PriorityRule("Flag Bearer", PriorityRule.resources("actions", ">=", 1)),
            # Duplicate is a Reserve set-aside; play when no better option
            PriorityRule("Duplicate"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule(
                "Copper",
                PriorityRule.and_(
                    PriorityRule.has_cards(["Charlatan", "Treasury"], 2),
                    PriorityRule.turn_number("<=", 12),
                ),
            ),
        ]

        self.treasure_priority = [
            PriorityRule("Sack of Loot"),
            PriorityRule("Gold"),
            PriorityRule("Stockpile"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_victoria_engine() -> EnhancedStrategy:
    return VictoriaEngine()
