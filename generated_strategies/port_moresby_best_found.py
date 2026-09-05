"""Best strategy found for the Port Moresby board (``boards/port_moresby.txt``).

See ``docs/port_moresby_best_strategy.md`` for the search and validation.

Chassis: the island-model champion evolved from the Double Quartermaster
Money seed (Messenger/Trail opener, up to three Quartermasters while the
game is young, two Barbarians, Gold, Silver until turn 12, Duchies from
five Provinces left, Coppers up to ten for Fountain), with its dead
Sculptor rule pruned. The Quartermaster policy is hand-written: gain
through the ordinary gain list (Silver early; after turn 12 the list falls
through to Coppers, which sit on the mat and still count for Fountain),
and take a banked Silver into hand when the hand plus that Quartermaster's
banked Silvers would reach a Province, or when the game is nearly over.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _hand_coins(player) -> int:
    return sum(c.stats.coins for c in player.hand if c.is_treasure)


class PortMoresbyBestFound(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Best Found"
        self.description = (
            "Triple Quartermaster money with a Messenger/Trail opener and two "
            "Barbarians; banked Silvers are cashed in toward a Province or in the endgame."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule(
                "Messenger",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Messenger", 1),
                    PriorityRule.turn_number("<=", 4),
                ),
            ),
            PriorityRule(
                "Trail",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Trail", 1),
                    PriorityRule.turn_number("<=", 4),
                ),
            ),
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 5)),
            PriorityRule(
                "Quartermaster",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Quartermaster", 3),
                    PriorityRule.turn_number("<=", 16),
                    PriorityRule.provinces_left(">", 4),
                ),
            ),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 2)),
            PriorityRule("Gold"),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 12)),
            PriorityRule("Copper", PriorityRule.max_in_deck("Copper", 10)),
        ]
        self.action_priority = [
            PriorityRule("Trail"),
            PriorityRule("Quartermaster"),
            PriorityRule("Barbarian"),
            PriorityRule("Messenger"),
        ]
        # Never trash Copper on this board (Fountain).
        self.trash_priority = [PriorityRule("Curse"), PriorityRule("Estate")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

    def choose_quartermaster_option(self, state, player, mat, candidates):
        """In order: (1) if this Quartermaster has banked Silvers, the hand is
        short of 8 coins, and either the hand plus 2 per banked Silver reaches 8
        or two or fewer Provinces remain, take one Silver into hand; (2) otherwise
        run the normal gain priority over the affordable cards and bank its pick;
        (3) otherwise bank a Silver if one is offered; (4) otherwise take the most
        expensive banked card; (5) otherwise bank the first offered card."""
        silvers = [c for c in mat if c.name == "Silver"]
        coins = _hand_coins(player)
        provinces = state.supply.get("Province", 0)
        if silvers and coins < 8 and (coins + 2 * len(silvers) >= 8 or provinces <= 2):
            return "take", silvers[0]
        gain = self.choose_gain(state, player, candidates + [None])
        if gain is not None and gain in candidates:
            return "gain", gain
        silver = next((c for c in candidates if c.name == "Silver"), None)
        if silver is not None:
            return "gain", silver
        if mat:
            return "take", max(mat, key=lambda c: (c.cost.coins, c.name))
        return "gain", (candidates[0] if candidates else None)


def create_port_moresby_best_found() -> EnhancedStrategy:
    return PortMoresbyBestFound()
