"""Hand-written strategy for the Wizards/Lich kingdom.

Board: Beggar, Lurker, Settlers/Bustling Village, Wishing Well,
       Student/Conjurer/Sorcerer/Lich, Mill, Baker, Cauldron, Crew, Pilgrim
Event: Continue        Ally: Cave Dwellers

Plan: open Student + Cauldron; trash through Estates/Coppers; race up the
Wizards pile; pick up Cauldron and Pilgrim for payload/draw; grab Bustling
Village once Settlers run out (Lurker accelerates this); end with multiple
Liches. Mill greens during engine turns.
"""

from .base_strategy import BaseStrategy, PriorityRule
from dominion.strategy.enhanced_strategy import EnhancedStrategy


class WizardsLichEngine(BaseStrategy):
    """Lich-payload engine fed by Student/Conjurer trashing and Cave Dwellers."""

    def __init__(self):
        super().__init__()
        self.name = "WizardsLichEngine"
        self.description = (
            "Wizards split-pile engine: Student trashing, Sorcerer/Cauldron "
            "cursing, Pilgrim draw, Lich payload. Cave Dwellers smooths shuffles."
        )
        self.version = "1.0"

        self.gain_priority = [
            # Greening
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),

            # --- Engine spine: race up the Wizards pile ---
            # Lich is the payload card — buy every copy you can.
            PriorityRule("Lich"),
            # Sorcerer for cursing + cantrip-Liaison.
            PriorityRule(
                "Sorcerer",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Sorcerer", 2),
                    PriorityRule.turn_number("<=", 16),
                ),
            ),
            # Conjurer is a cantrip that gains a $4 — perfect for Mill/Conjurer chains.
            PriorityRule(
                "Conjurer",
                PriorityRule.max_in_deck("Conjurer", 2),
            ),
            # Student opens trashing + Favors. Want exactly one early.
            PriorityRule(
                "Student",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Student", 1),
                    PriorityRule.turn_number("<=", 8),
                ),
            ),

            # --- Payload cards ---
            # Pilgrim: terminal +4 draw with topdeck. Cave Dwellers cleans up junk.
            PriorityRule(
                "Pilgrim",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Pilgrim", 2),
                    PriorityRule.turn_number("<=", 14),
                ),
            ),
            # Cauldron: $2 + buy treasure that curses on third gain. Auto-include.
            PriorityRule(
                "Cauldron",
                PriorityRule.max_in_deck("Cauldron", 2),
            ),
            # Bustling Village is the only village. Buy when exposed.
            PriorityRule("Bustling Village"),
            # Mid-engine money + cantrip-VP.
            PriorityRule(
                "Mill",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Mill", 3),
                    PriorityRule.turn_number(">=", 5),
                ),
            ),
            # Baker for Coffer smoothing.
            PriorityRule(
                "Baker",
                PriorityRule.max_in_deck("Baker", 1),
            ),
            # Lurker accelerates Settlers and Wizards drains; cheap non-terminal.
            PriorityRule(
                "Lurker",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Lurker", 2),
                    PriorityRule.turn_number("<=", 12),
                ),
            ),
            # Gold as backup economy
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            # One Wishing Well as a $3 cantrip (peeks the deck).
            PriorityRule(
                "Wishing Well",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Wishing Well", 1),
                    PriorityRule.turn_number("<=", 8),
                ),
            ),
            # Silver as fallback when nothing better is affordable.
            PriorityRule("Silver", PriorityRule.provinces_left(">", 3)),
        ]

        self.action_priority = [
            # Villages/cantrips first.
            PriorityRule("Bustling Village"),
            PriorityRule("Settlers"),
            PriorityRule("Mill"),
            PriorityRule("Wishing Well"),
            # Liaisons / Wizards. Lich needs +2 actions; play it before Pilgrim
            # so we keep terminal slots open.
            PriorityRule("Lich"),
            PriorityRule("Conjurer"),
            PriorityRule("Sorcerer"),
            PriorityRule("Student"),
            PriorityRule("Baker"),
            # Lurker is non-terminal — play whenever, but after villages.
            PriorityRule("Lurker"),
            # Terminal draw last.
            PriorityRule("Pilgrim"),
            PriorityRule("Crew"),
            # Beggar gives 3 Coppers — only play if no trasher available.
            PriorityRule("Beggar"),
        ]

        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Cauldron"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule("Hovel"),
            PriorityRule("Overgrown Estate"),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver"], 2)),
        ]


def create_wizards_lich_engine() -> EnhancedStrategy:
    return WizardsLichEngine()
