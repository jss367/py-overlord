from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _card_count_less_than(card_name: str, limit: int):
    return lambda _state, player: player.count_in_deck(card_name) < limit


def _colonies_left(op: str, amount: int):
    cmp = PriorityRule._OP_MAP[op]
    return lambda state, _player: cmp(state.supply.get("Colony", 0), amount)


def _peddler_cost_at_most(amount: int):
    def _condition(state, player):
        return state.get_card_cost(player, get_card("Peddler")) <= amount

    return _condition


class ClerkCollectionColonyStrategy(EnhancedStrategy):
    """Clerk-backed Collection/Peddler engine for the Watchtower Colony board."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "ClerkCollectionColony"
        self.description = (
            "Builds around early Clerk pressure, Collection VP, cheap Peddlers, "
            "and Platinum into Colonies."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("Province", _colonies_left("<=", 3)),
            PriorityRule("Duchy", _colonies_left("<=", 2)),
            PriorityRule("Platinum"),
            PriorityRule("Peddler", _peddler_cost_at_most(2)),
            PriorityRule("Clerk", _card_count_less_than("Clerk", 3)),
            PriorityRule("Collection", _card_count_less_than("Collection", 3)),
            PriorityRule("City", _card_count_less_than("City", 5)),
            PriorityRule("Workers' Village", _card_count_less_than("Workers' Village", 5)),
            PriorityRule("Festival", _card_count_less_than("Festival", 4)),
            PriorityRule("Peddler"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
        ]

        self.action_priority = [
            PriorityRule("City"),
            PriorityRule("Workers' Village"),
            PriorityRule("Festival"),
            PriorityRule("Peddler"),
            PriorityRule("Clerk"),
            PriorityRule("Watchtower"),
        ]

        self.treasure_priority = [
            PriorityRule("Collection"),
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Investment"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", _colonies_left(">", 3)),
            PriorityRule(
                "Copper",
                PriorityRule.and_(
                    PriorityRule.has_cards(["Platinum", "Gold"], 3),
                    _colonies_left(">", 2),
                ),
            ),
        ]


def create_clerk_collection_colony() -> EnhancedStrategy:
    return ClerkCollectionColonyStrategy()
