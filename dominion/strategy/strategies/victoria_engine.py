from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _opponent_holds_flag(state, player) -> bool:
    flag = state.artifacts.get("Flag") if hasattr(state, "artifacts") else None
    return flag is not None and flag.holder is not None and flag.holder is not player


class VictoriaEngine(EnhancedStrategy):
    """Charlatan engine for the Victoria board with the Flag Bearer butterfly trick.

    Core plan: thin with Sailor + Change, draw with Wayfarer, glue with Treasury,
    payload with Charlatan, double with Daimyo. Flag Bearer is bought repeatedly
    and Butterfly'd into a $5 card (Charlatan/Treasury) — Way of the Butterfly
    returns it to the supply rather than trashing it, so the Flag artifact stays
    with us through every Butterfly play. Re-buy Flag Bearer whenever an
    opponent steals the Flag.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "VictoriaEngine"
        self.description = "Charlatan engine + Flag Bearer butterfly upgrader"
        self.version = "2.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.has_cards(["Charlatan", "Wayfarer"], 3)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),

            # Defensive Flag re-claim — fires whenever an opponent has the Flag.
            PriorityRule("Flag Bearer", _opponent_holds_flag),
            # Initial Flag claim.
            PriorityRule("Flag Bearer", PriorityRule.max_in_deck("Flag Bearer", 1)),

            PriorityRule(
                "Daimyo",
                PriorityRule.and_(
                    PriorityRule.has_cards(["Charlatan", "Wayfarer"], 2),
                    PriorityRule.max_in_deck("Daimyo", 2),
                ),
            ),
            PriorityRule(
                "Sack of Loot",
                PriorityRule.has_cards(["Charlatan", "Wayfarer"], 3),
            ),
            PriorityRule("Wayfarer", PriorityRule.max_in_deck("Wayfarer", 2)),
            PriorityRule("Charlatan", PriorityRule.max_in_deck("Charlatan", 4)),
            PriorityRule("Treasury", PriorityRule.max_in_deck("Treasury", 3)),
            PriorityRule("Sailor", PriorityRule.max_in_deck("Sailor", 2)),
            PriorityRule(
                "Change",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Change", 1),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
            PriorityRule(
                "Duplicate",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Duplicate", 1),
                    PriorityRule.has_cards(["Charlatan", "Treasury"], 1),
                ),
            ),

            PriorityRule(
                "Stockpile",
                PriorityRule.and_(
                    PriorityRule.turn_number("<=", 2),
                    PriorityRule.max_in_deck("Stockpile", 1),
                ),
            ),

            PriorityRule("Gold"),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 8)),
        ]

        self.action_priority = [
            PriorityRule("Treasury"),
            PriorityRule("Daimyo"),
            PriorityRule("Sailor"),
            PriorityRule("Wayfarer", PriorityRule.resources("actions", ">=", 1)),
            PriorityRule("Charlatan", PriorityRule.resources("actions", ">=", 1)),
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
            PriorityRule("Flag Bearer", PriorityRule.resources("actions", ">=", 1)),
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

    def choose_way(self, state, player, card, ways):
        # Butterfly Flag Bearer ($4) into a $5 whenever it's our only Flag
        # Bearer in hand. Returning to supply isn't a trash, so the Flag
        # artifact stays with us — net result is a free upgrade plus the
        # ability to re-buy Flag Bearer later for another upgrade.
        if (
            card.name == "Flag Bearer"
            and sum(1 for c in player.hand if c.name == "Flag Bearer") == 1
        ):
            target = self._best_butterfly_target(state, player, card.cost.coins + 1)
            if target:
                for w in ways:
                    if w and getattr(w, "name", None) == "Way of the Butterfly":
                        return w
        return super().choose_way(state, player, card, ways)


def create_victoria_engine() -> EnhancedStrategy:
    return VictoriaEngine()
