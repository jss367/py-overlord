"""Winning strategy on the lisbon board.

Kingdom (boards/lisbon.txt): Watchtower, Clerk, Gardens, Investment,
Workers' Village, City, Collection, Festival, Expand, Peddler — with
Colony and Platinum.

Genealogy: evolved by ``evolve.py`` from the ``LisbonCityPileout`` seed
against the ``LisbonFwpEngine`` baseline (population 25, 40 generations,
50 games/eval). Final tournament: 97.0% win rate over 5,600 games against
all four seeds and the other three evolved variants.

Why it works:
- City + Workers' Village + Festival make a non-thinning engine reliable
  enough to hit $11 Colony swings repeatedly.
- The gain list elevates City and Clerk above Province@$8: an extra
  $5 cantrip is worth more than a Province in mid-game until the engine
  is dense.
- ``Estate when City-in-play`` is a deliberate 3-pile signal: once City
  is firing, Estate gains both empty the pile and stoke City's bonus.
- ``Expand`` is gated to "Workers' Village in play and ≤1 card gained
  this turn" — i.e. fire it as a non-terminal trasher only when the
  chain has actions to spare and we haven't already burnt the buy on
  another gain.
- Treasure order leads with Collection so its +1 VP-per-action-gained
  hook is in play before any action gains resolve.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class LisbonCityEngine(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Lisbon City Engine"
        self.description = (
            "Evolved City + Workers' Village + Festival engine for the "
            "lisbon Colony board (97.0% in panel tournament)."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("City"),
            PriorityRule("Clerk"),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Collection"),
            PriorityRule("Silver", PriorityRule.terminals_in_hand("<=", 3)),
            PriorityRule("Peddler"),
            PriorityRule("Gold"),
            PriorityRule("Estate", PriorityRule.card_in_play("City")),
            PriorityRule("Investment"),
            PriorityRule("Silver", PriorityRule.resources("coins", ">=", 3)),
            PriorityRule("Watchtower"),
            PriorityRule("Workers' Village"),
            PriorityRule("Platinum", PriorityRule.turn_number("<=", 11)),
            PriorityRule("Expand"),
        ]

        self.action_priority = [
            PriorityRule("City"),
            PriorityRule("Festival"),
            PriorityRule("Clerk"),
            PriorityRule("Watchtower"),
            PriorityRule(
                "Expand",
                PriorityRule.and_(
                    PriorityRule.card_in_play("Workers' Village"),
                    PriorityRule.cards_gained_this_turn("<=", 1),
                ),
            ),
        ]

        self.treasure_priority = [
            PriorityRule("Collection"),
            PriorityRule("Platinum"),
            PriorityRule("Investment"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]


def create_lisbon_city_engine() -> EnhancedStrategy:
    return LisbonCityEngine()
