"""Island seed: Festival Big Money + Collection for Lisbon.

Theory of victory
-----------------
Big Money with two thoughtful upgrades: Festival as a one-shot terminal
that turns a $4 hand into $6 with +1 buy, and Collection as a treasure
that adds VP every time we incidentally gain an Action (Festival,
Watchtower) on the way to Colonies.

This is the speed-test archetype. If a deck this simple is even close
to the engines, the engines are over-thinking the kingdom.

Plan
----
- Open Silver + Silver or Silver + Watchtower (Clerk defense).
- Buy Gold/Silver normally. Pick up 1-2 Festivals for the +1 buy and
  the +$2 (Festival itself doesn't draw, so don't stack more than 2).
- Pick up 2-3 Collections — each gain of an Action while Collection is
  in play scores +1 VP token. Even one Festival gain per turn over a
  Big Money game adds up.
- One Watchtower for Clerk reaction defense.
- Buy Colonies aggressively from turn 8-10 onward.

Why this is on the panel
------------------------
This is the "is the GA being unfair to Big Money?" check. The City
Pile Engine docstring says BM is "too easy to crush" — this seed asks
how true that is when BM is allowed to use the kingdom's cards.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class LisbonFestivalBigMoney(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Lisbon Festival BigMoney"
        self.description = (
            "Big Money chassis with Festival, Collection, and a defensive "
            "Watchtower. The speed-test baseline for Lisbon."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Festival", PriorityRule.max_in_deck("Festival", 2)),
            PriorityRule("Collection", PriorityRule.max_in_deck("Collection", 3)),
            PriorityRule("Watchtower", PriorityRule.max_in_deck("Watchtower", 1)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 10)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            PriorityRule("Festival"),
            PriorityRule("Watchtower"),
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
        ]


def create_lisbon_festival_bigmoney() -> EnhancedStrategy:
    return LisbonFestivalBigMoney()
