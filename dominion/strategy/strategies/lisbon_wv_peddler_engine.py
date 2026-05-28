"""Island seed: Workers' Village / Peddler / Expand Engine for Lisbon.

Theory of victory
-----------------
A true engine that does not depend on City's piling-out trick. Workers'
Village is a $4 *village* that also gives +1 buy — the foundation of the
deck. Festival provides the terminal $2/+1 buy explosion. Peddler costs
$8 normally but drops by $2 per Action in play during the Buy phase, so
with 3+ actions in play it's a free cantrip-economy card.

Plan
----
- Open Silver + Silver (or Workers' Village + Silver).
- Pile up Workers' Villages and Festivals through turn 7.
- Once 3-4 actions are in play per turn, start gaining Peddlers for $2
  or $0 each.
- Use Expand to upgrade Estates/Coppers into Gold or Workers' Village,
  reserving it for turns where Workers' Village is in play (non-terminal
  use) and we haven't already burned the buy.
- Collection is a treasure that adds +$2/+1 buy AND gives +1 VP per
  Action gained while in play. Pick up 2-3 to convert gain pressure
  into a steady VP drip without slowing down.
- Buy Colonies once we can repeatably hit $11.

Why this is on the panel
------------------------
This is the "obvious" strong engine for the board. If the City Pile
Engine genuinely beats this, then the City pile-out trick is the real
deal. If this beats it, the original GA found a local optimum.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class LisbonWvPeddlerEngine(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Lisbon WV Peddler Engine"
        self.description = (
            "Workers' Village + Festival draw engine with Peddler economy "
            "and Expand upgrades. The 'obvious' strong engine for Lisbon."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Workers' Village", PriorityRule.max_in_deck("Workers' Village", 5)),
            PriorityRule("Festival", PriorityRule.max_in_deck("Festival", 4)),
            PriorityRule("Peddler", PriorityRule.actions_in_play(">=", 3)),
            PriorityRule("Gold"),
            PriorityRule("Expand", PriorityRule.max_in_deck("Expand", 2)),
            PriorityRule("Collection", PriorityRule.max_in_deck("Collection", 3)),
            PriorityRule("Platinum", PriorityRule.turn_number("<=", 12)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 6)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            PriorityRule("Workers' Village"),
            PriorityRule("Festival"),
            PriorityRule("Peddler"),
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
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]


def create_lisbon_wv_peddler_engine() -> EnhancedStrategy:
    return LisbonWvPeddlerEngine()
