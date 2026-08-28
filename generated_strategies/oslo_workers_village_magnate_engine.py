"""Workers' Village/Magnate engine family for the discounted Oslo board.

Includes the user's hand-built seed and the strongest constrained evolution
found from that seed. The evolved policy keeps every mandatory engine piece;
only the optional package and timing/copy limits were allowed to change.
"""

from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _opening_anvil(limit: int, through_turn: int):
    return PriorityRule.and_(
        PriorityRule.max_in_deck("Anvil", limit),
        PriorityRule.cards_gained_this_turn("==", 0),
        PriorityRule.turn_number("<=", through_turn),
    )


def _hold_copper_for_anvil(village_limit: int, magnate_limit: int):
    """Leave Copper in hand only while Anvil can gain a needed engine card."""

    def condition(state, player):
        if not any(card.name == "Anvil" for card in player.in_play):
            return True
        needs_village = (
            player.count_in_deck("Workers' Village") < village_limit
            and state.supply.get("Workers' Village", 0) > 0
        )
        needs_magnate = (
            player.count_in_deck("Magnate") < magnate_limit
            and state.supply.get("Magnate", 0) > 0
        )
        return not (needs_village or needs_magnate)

    return condition


def _hold_copper_for_seed_engine():
    """Seed policy: preserve Copper for Anvil or an immediately affordable Market."""

    anvil_condition = _hold_copper_for_anvil(5, 5)

    def condition(state, player):
        if not anvil_condition(state, player):
            return False
        if (
            player.count_in_deck("Grand Market") < 3
            and state.supply.get("Grand Market", 0) > 0
            and player.coins >= state.get_card_cost(player, get_card("Grand Market"))
        ):
            return False
        return True

    return condition


def _multi_colony_greening_gate(min_colonies: int, fallback_turn: int):
    """Delay the first Colony until one turn can buy ``min_colonies`` of them.

    Before any Colony is owned, only green on a turn whose buy-phase coins and
    buys cover ``min_colonies`` Colonies at the current (discounted) cost, so
    the engine keeps building instead of trickling out single Colonies. Once
    the first Colony is bought the gate stays open, and it always opens at
    ``fallback_turn`` so the deck cannot build forever.
    """

    def condition(state, player):
        if player.count_in_deck("Colony") > 0:
            return True
        if state.turn_number >= fallback_turn:
            return True
        cost = state.get_card_cost(player, get_card("Colony"))
        return player.buys >= min_colonies and player.coins >= min_colonies * cost

    return condition


def _province_after_two_colonies_or_turn_18():
    return PriorityRule.or_(
        PriorityRule.colonies_left("<=", 2),
        PriorityRule.turn_number(">=", 18),
    )


def _kings_court_after_three_magnates():
    return PriorityRule.and_(
        PriorityRule.max_in_deck("King's Court", 3),
        PriorityRule.has_cards(["Magnate"], 3),
    )


class OsloWorkersVillageMagnateStartingStrategy(EnhancedStrategy):
    """Direct implementation of the proposed starting strategy."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Oslo Workers' Village Magnate Starting Strategy"
        self.description = (
            "Workers' Village/Magnate draw with Anvil acceleration, two Banks, "
            "three King's Courts, and optional payload cards."
        )

        self.gain_priority = [
            PriorityRule("Anvil", _opening_anvil(1, 7)),
            PriorityRule("Colony"),
            PriorityRule("Workers' Village", PriorityRule.max_in_deck("Workers' Village", 5)),
            PriorityRule("Magnate", PriorityRule.max_in_deck("Magnate", 5)),
            PriorityRule("King's Court", PriorityRule.max_in_deck("King's Court", 3)),
            PriorityRule("Bank", PriorityRule.max_in_deck("Bank", 2)),
            PriorityRule("Hoard", PriorityRule.max_in_deck("Hoard", 1)),
            PriorityRule("Grand Market", PriorityRule.max_in_deck("Grand Market", 3)),
            PriorityRule("Province", PriorityRule.colonies_left("<=", 4)),
            PriorityRule("Expand", PriorityRule.max_in_deck("Expand", 1)),
            PriorityRule("Platinum", PriorityRule.max_in_deck("Platinum", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Workers' Village"),
            PriorityRule("Grand Market"),
            PriorityRule("King's Court"),
            PriorityRule("Magnate"),
            PriorityRule("Expand"),
        ]
        self.treasure_priority = [
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Hoard"),
            PriorityRule("Silver"),
            PriorityRule("Anvil"),
            PriorityRule("Copper", _hold_copper_for_seed_engine()),
            PriorityRule("Bank"),
        ]
        self.trash_priority = [
            PriorityRule("Estate", PriorityRule.colonies_left(">", 2)),
            PriorityRule("Copper"),
            PriorityRule("Silver"),
            PriorityRule("Gold"),
        ]


class OsloWorkersVillageMagnateEngine(EnhancedStrategy):
    """Best constrained evolution of the Workers' Village/Magnate family."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Oslo Workers' Village Magnate Engine"
        self.description = (
            "Seven-Village/seven-Magnate engine accelerated by two Anvils, "
            "with two Banks, three King's Courts, one Hoard, and two Grand Markets."
        )

        self.gain_priority = [
            PriorityRule("Anvil", _opening_anvil(2, 6)),
            PriorityRule("Colony"),
            PriorityRule("Province", PriorityRule.colonies_left("<=", 2)),
            PriorityRule("Bank", PriorityRule.max_in_deck("Bank", 2)),
            PriorityRule("King's Court", PriorityRule.max_in_deck("King's Court", 3)),
            PriorityRule("Workers' Village", PriorityRule.max_in_deck("Workers' Village", 7)),
            PriorityRule("Hoard", PriorityRule.max_in_deck("Hoard", 1)),
            PriorityRule("Grand Market", PriorityRule.max_in_deck("Grand Market", 2)),
            PriorityRule("Platinum", PriorityRule.max_in_deck("Platinum", 1)),
            PriorityRule("Magnate", PriorityRule.max_in_deck("Magnate", 7)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 1)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Workers' Village"),
            PriorityRule("Grand Market"),
            PriorityRule("King's Court"),
            PriorityRule("Magnate"),
        ]
        self.treasure_priority = [
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Hoard"),
            PriorityRule("Silver"),
            PriorityRule("Anvil"),
            PriorityRule("Copper", _hold_copper_for_anvil(7, 7)),
            # Bank comes last so it counts every Treasure actually played.
            PriorityRule("Bank"),
        ]


class OsloWorkersVillageMagnateRefinedEngine(EnhancedStrategy):
    """Second constrained evolution with balanced Anvil gains and phase gates."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Oslo Workers' Village Magnate Refined Engine"
        self.description = (
            "Balanced seven-Village/seven-Magnate engine; King's Court waits "
            "for three Magnates and Provinces begin by round 18."
        )

        self.gain_priority = [
            PriorityRule("Anvil", _opening_anvil(2, 7)),
            PriorityRule("Colony"),
            PriorityRule("Province", _province_after_two_colonies_or_turn_18()),
            PriorityRule("Bank", PriorityRule.max_in_deck("Bank", 2)),
            PriorityRule("King's Court", _kings_court_after_three_magnates()),
            PriorityRule("Workers' Village", PriorityRule.max_in_deck("Workers' Village", 7)),
            PriorityRule("Hoard", PriorityRule.max_in_deck("Hoard", 1)),
            PriorityRule("Platinum", PriorityRule.max_in_deck("Platinum", 1)),
            PriorityRule("Magnate", PriorityRule.max_in_deck("Magnate", 7)),
            PriorityRule("Grand Market", PriorityRule.max_in_deck("Grand Market", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 1)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Workers' Village"),
            PriorityRule("Grand Market"),
            PriorityRule("King's Court"),
            PriorityRule("Magnate"),
        ]
        self.treasure_priority = [
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Hoard"),
            PriorityRule("Silver"),
            PriorityRule("Anvil"),
            PriorityRule("Copper", _hold_copper_for_anvil(7, 7)),
            PriorityRule("Bank"),
        ]

    def choose_anvil_gain(self, state, player, choices):
        """Gain whichever of Village/Magnate is further below its target ratio."""

        targets = [
            card
            for card in choices
            if card is not None
            and card.name in {"Workers' Village", "Magnate"}
            and player.count_in_deck(card.name) < 7
        ]
        if targets:
            return min(targets, key=lambda card: player.count_in_deck(card.name) / 7)
        return self.choose_gain(state, player, choices)


class OsloWorkersVillageMagnateMultiColonyEngine(OsloWorkersVillageMagnateRefinedEngine):
    """Refined engine that waits for a double-Colony turn before greening."""

    def __init__(
        self,
        min_colonies: int = 4,
        fallback_turn: int = 20,
        province_turn: int = 18,
    ) -> None:
        super().__init__()
        self.name = "Oslo Workers' Village Magnate Multi Colony Engine"
        self.description = (
            "Refined engine variant that keeps building until a single turn "
            f"can buy {min_colonies} Colonies, then greens normally "
            f"(forced open at turn {fallback_turn})."
        )
        for rule in self.gain_priority:
            if rule.card_name == "Colony":
                rule.condition = _multi_colony_greening_gate(min_colonies, fallback_turn)
            elif rule.card_name == "Province" and province_turn != 18:
                rule.condition = PriorityRule.or_(
                    PriorityRule.colonies_left("<=", 2),
                    PriorityRule.turn_number(">=", province_turn),
                )


def create_oslo_workers_village_magnate_starting_strategy() -> EnhancedStrategy:
    return OsloWorkersVillageMagnateStartingStrategy()


def create_oslo_workers_village_magnate_engine() -> EnhancedStrategy:
    return OsloWorkersVillageMagnateEngine()


def create_oslo_workers_village_magnate_refined_engine() -> EnhancedStrategy:
    return OsloWorkersVillageMagnateRefinedEngine()


def create_oslo_workers_village_magnate_multi_colony_engine() -> EnhancedStrategy:
    return OsloWorkersVillageMagnateMultiColonyEngine()
