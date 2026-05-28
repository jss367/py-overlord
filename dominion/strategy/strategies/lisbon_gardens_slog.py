"""Island seed: Gardens Slog for Lisbon.

Theory of victory
-----------------
There are no thinners on the Lisbon board (no Chapel, no Remake, no
Sentry). Every deck stays bloated. Gardens scores 1 VP per 10 cards.
Workers' Village gives +1 card / +2 actions / +1 buy — the perfect
gain-engine for stacking buys per turn. Festival adds +1 buy on top.

Plan
----
- Open Silver + Silver.
- Buy Workers' Villages and Festivals aggressively for the +1 buy.
- Snap up Gardens early (the pile is only 8 in a 2p game; an opponent
  may also want them).
- Late game, spend extra buys on Copper and Estate to bloat the deck
  count AND empty piles for a 3-pile finish. 30-40 cards = 3-4 Gardens
  apiece, plus a few Estates and Duchies, totals 20+ VP in a Colony
  game that the opponent might struggle to match without thinning.
- Avoid Province/Colony entirely until the 3-pile finish — they're
  expensive and we don't need the VP.

Why this is on the panel
------------------------
A slog archetype attacks the engine archetypes on a different VP axis.
City Pile Engine wants the City pile empty; Gardens Slog wants three
piles empty AND tons of junk. They could collide productively or the
slog could just be too slow. Worth testing.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class LisbonGardensSlog(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Lisbon Gardens Slog"
        self.description = (
            "No-Province slog: Gardens + Workers' Village + Festival, pile "
            "out on cheap cards and copper-stuffing for the 3-pile ending."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Gardens", PriorityRule.max_in_deck("Gardens", 8)),
            PriorityRule("Workers' Village", PriorityRule.max_in_deck("Workers' Village", 8)),
            PriorityRule("Festival", PriorityRule.max_in_deck("Festival", 6)),
            PriorityRule("Watchtower", PriorityRule.max_in_deck("Watchtower", 2)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 8)),
            PriorityRule("Duchy", PriorityRule.empty_piles(">=", 1)),
            PriorityRule("Estate", PriorityRule.empty_piles(">=", 1)),
            PriorityRule("Copper", PriorityRule.empty_piles(">=", 1)),
            PriorityRule("Silver"),
        ]

        self.action_priority = [
            PriorityRule("Workers' Village"),
            PriorityRule("Festival"),
            PriorityRule("Watchtower"),
        ]

        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
        ]


def create_lisbon_gardens_slog() -> EnhancedStrategy:
    return LisbonGardensSlog()
