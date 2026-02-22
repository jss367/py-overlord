"""Strategy for the Wharf kingdom board.

Board: Wharf, Wealthy Village, Wild Hunt (Tireless), Pirate, Gatekeeper,
       Cauldron, Cartographer, Berserker, Aristocrat, Harbor Village
Event: Training

Core engine: Harbor Village for actions, Wharf for draw + buy, Wild Hunt
(Tireless) for guaranteed draw every turn.  Training on Wharf or Wild Hunt
for extra economy.  Gatekeeper as payload for $6 over two turns plus
opponent disruption.
"""

from .base_strategy import BaseStrategy, PriorityRule
from dominion.strategy.enhanced_strategy import EnhancedStrategy


class WharfWildHuntEngine(BaseStrategy):
    """Wharf + Tireless Wild Hunt engine with Harbor Village actions."""

    def __init__(self):
        super().__init__()
        self.name = "WharfWildHuntEngine"
        self.description = (
            "Engine built around Wharf draw, Tireless Wild Hunt for "
            "guaranteed card draw, Harbor Village for actions, and "
            "Training for economy."
        )
        self.version = "1.0"

        # === GAIN PRIORITIES ===
        # Core approach: Wharf-centric money with Wild Hunt (Tireless)
        # for guaranteed draw and Gatekeeper for economy/attack.
        # Keep the deck lean - few actions, lots of treasure.
        self.gain_priority = [
            # Province is the goal
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            # Duchy in endgame
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            # Estate when game is nearly over
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),

            # --- Key engine pieces (limited) ---
            # Wharf first: +2 Cards +1 Buy lasting two turns is the best card.
            # Get 2 Wharves.
            PriorityRule(
                "Wharf",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Wharf", 2),
                    PriorityRule.turn_number("<=", 12),
                ),
            ),
            # Gatekeeper: $3 now + $3 next turn. Powerful economy + disruption.
            # 1 copy is enough as a terminal.
            PriorityRule(
                "Gatekeeper",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Gatekeeper", 1),
                    PriorityRule.turn_number("<=", 10),
                ),
            ),
            # Gold is always strong
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            # Wild Hunt with Tireless: guaranteed +3 Cards every turn.
            # Extremely powerful but terminal. Get exactly 1, after some economy.
            PriorityRule(
                "Wild Hunt",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Wild Hunt", 1),
                    lambda _s, me: me.count_in_deck("Wharf") >= 1,
                ),
            ),
            # Harbor Village: needed to support multiple terminals
            PriorityRule(
                "Harbor Village",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Harbor Village", 1),
                    lambda _s, me: (
                        me.count_in_deck("Wharf") + me.count_in_deck("Wild Hunt")
                        + me.count_in_deck("Gatekeeper") >= 2
                    ),
                ),
            ),
            # Silver: essential early economy
            PriorityRule("Silver", PriorityRule.provinces_left(">", 2)),
        ]

        # === ACTION PRIORITIES ===
        self.action_priority = [
            # Harbor Village first for +2 Actions
            PriorityRule("Harbor Village"),
            # Wild Hunt: draw 3 cards (Tireless brings it back)
            PriorityRule("Wild Hunt"),
            # Wharf: draw 2 + buy (Duration)
            PriorityRule("Wharf"),
            # Gatekeeper: $3 economy + attack
            PriorityRule("Gatekeeper"),
            # Cartographer: deck filtering
            PriorityRule("Cartographer"),
            # Other terminals if somehow gained
            PriorityRule("Berserker"),
            PriorityRule("Wealthy Village"),
            PriorityRule("Pirate"),
            PriorityRule("Aristocrat"),
        ]

        # === TREASURE PRIORITIES ===
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Cauldron"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        # === TRASH PRIORITIES ===
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
        ]


def create_wharf_wild_hunt_engine() -> EnhancedStrategy:
    """Factory function for Wharf + Wild Hunt engine strategy."""
    return WharfWildHuntEngine()
