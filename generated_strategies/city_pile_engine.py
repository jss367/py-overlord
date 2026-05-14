"""City Pile Engine — refined strategy for boards/lisbon.txt.

Kingdom: Watchtower, Clerk, Gardens, Investment, Workers' Village, City,
Collection, Festival, Expand, Peddler — with Colony and Platinum.

Genealogy
---------
Seeded from ``LisbonCityEngine`` (the 97%-vs-baseline winner introduced
in PR #243) and re-evolved twice under panel pressure:

- Round 1 panel: v1 LisbonCityEngine + ClerkCollectionColony (PR #250)
  + the prior panel-evolved FWP engine. No Big Money on the panel —
  too easy to crush, doesn't drive learning.
- Round 2 panel: above three plus the round-1 winner itself, so any
  further improvement has to beat the immediate ancestor.

Both rounds converged on essentially this same priority list. The
empirical pruning from PR #244 compressed the genome from v1's 15+5
rules down to 6+3. Everything in this file actually fires during play.

Empirical performance (400-game head-to-heads)
-----------------------------------------------
- vs v1 LisbonCityEngine (PR #243):      52.0%  margin +2.5
- vs ClerkCollectionColony (PR #250):    65.2%  margin +9.4
- vs prior panel-evolved FWP engine:     83.8%  margin +23.5

Average across the panel: ~63%, vs v1's ~60%. The improvement vs v1
itself is within statistical noise on a single matchup, but the
strategy is meaningfully more robust against the broader field — it
generalizes better, especially against the cantrip-payload FWP
archetype where v1 only wins ~76%.

Why this works
--------------
The core trick is **City pile-out**. City at base mode is just
+1 card +2 actions; with 1 empty pile in supply it adds +1 card +$1;
with 2 empty piles it adds +1 buy +$1. So a deck of 7-10 Cities
quietly becomes a multi-buy $20+/turn engine once Clerk and City
piles deplete.

- ``City`` at rule 1 of the gain list means we buy City at every
  affordable price point ($5-$10) until that pile empties. After it
  empties, the rule falls through to ``Colony``.
- ``Colony`` is unconditional, placed below City in the walk order.
  The GA originally produced a ``provinces_left <= 8`` gate here,
  which is vacuously true in 2-player play (Province pile starts at
  8) but would block Colony purchases in 3+ player games until
  several Provinces had been bought (pile starts at 12 there). The
  gate is dropped so this strategy works correctly at any seat
  count.
- ``Clerk`` at rule 3 backstops every $4 hand and supplies terminal
  +$2 plus a topdeck attack on opponent.
- ``Peddler`` is bought through turn 14 — once the action chain is
  running its cost drops below $4, so it slots in cheaply as deck-bulk.
- ``Gardens`` after turn 12 — a late-game alt-VP splash that v1
  missed entirely. The pile-out engine builds a 25-30 card deck, so
  2-3 Gardens add 6-9 VP at zero engine cost.
- ``Silver`` only when terminals in hand are ≤3 — avoids
  over-thickening the deck with junk treasures when terminal payload
  is already covered.

The ``action_priority`` includes ``Watchtower`` even though the gain
list never buys it; that's a harmless artifact preserved from the
seed in case opponent effects ever hand us one (no opponent on this
board does).
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class CityPileEngine(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "City Pile Engine"
        self.description = (
            "Panel-evolved City pile-out engine for the lisbon Colony "
            "board. Buys City until pile empty, then Colony; late "
            "Gardens splash for alt-VP."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("City"),
            PriorityRule("Colony"),
            PriorityRule("Clerk"),
            PriorityRule("Peddler", PriorityRule.turn_number("<=", 14)),
            PriorityRule("Gardens", PriorityRule.turn_number(">", 12)),
            PriorityRule("Silver", PriorityRule.terminals_in_hand("<=", 3)),
        ]

        self.action_priority = [
            PriorityRule("City"),
            PriorityRule("Watchtower"),
            PriorityRule("Clerk"),
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
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule(
                "Copper",
                PriorityRule.has_cards(["Silver", "Gold"], 3),
            ),
        ]


def create_city_pile_engine() -> EnhancedStrategy:
    return CityPileEngine()
