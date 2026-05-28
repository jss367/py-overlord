"""Island seed: Watchtower Topdeck Engine for Lisbon.

Theory of victory
-----------------
Watchtower is a draw-to-6 cantrip AND a reaction that lets you topdeck
or trash a gained card. The reaction transforms how Expand and
Investment interact with deck composition: gain a Gold via Expand →
topdeck it → it shows up in the next hand. Gain a Workers' Village →
topdeck it → guaranteed engine fuel next turn.

Plan
----
- Open Watchtower + Silver.
- Buy a second Watchtower around turn 3-4.
- Expand becomes a deck-shaping tool: trash Estate → gain Workers'
  Village → topdeck via Watchtower → use it next turn. Trash Silver →
  gain Festival → topdeck. Trash Festival → gain Gold → topdeck.
- Investment provides additional gain pressure: each turn it trashes
  a junk card (with Watchtower in hand to topdeck the next gain).
- Workers' Village and Festival fill out the engine; Peddler stays
  expensive without 3+ actions in play.

Why this is on the panel
------------------------
Watchtower's reaction is the kingdom's hidden synergy — it punishes
strategies that ignore it. The City Pile Engine treats Watchtower as
an afterthought (it's #12 in its gain list). If a Watchtower-centric
build wins, the GA missed a real combo.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class LisbonWatchtowerTopdeck(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Lisbon Watchtower Topdeck"
        self.description = (
            "Watchtower-as-engine: reaction topdecks every important gain. "
            "Expand and Investment as the gain-pressure tools."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Watchtower", PriorityRule.max_in_deck("Watchtower", 2)),
            PriorityRule("Workers' Village", PriorityRule.max_in_deck("Workers' Village", 4)),
            PriorityRule("Gold"),
            PriorityRule("Expand", PriorityRule.max_in_deck("Expand", 2)),
            PriorityRule("Festival", PriorityRule.max_in_deck("Festival", 3)),
            PriorityRule("Investment", PriorityRule.max_in_deck("Investment", 3)),
            PriorityRule("Platinum", PriorityRule.turn_number("<=", 12)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 6)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            PriorityRule("Workers' Village"),
            PriorityRule("Festival"),
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
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Investment"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]


def create_lisbon_watchtower_topdeck() -> EnhancedStrategy:
    return LisbonWatchtowerTopdeck()
