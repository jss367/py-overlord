"""Strategy for the Cauldron-curse seed board.

Board: Cauldron, Settlers, Wishing Well, Pawn, Hamlet, Workshop, Village,
       Smithy, Mill, Baker

Plan:
    Cauldron (Hinterlands) is a $3 treasure-attack reading: "+$2, +1 Buy.
    When you have three or more Action cards gained this turn while at
    least one Cauldron is in play, each opponent gains a Curse."

    The trigger lives in
    :func:`dominion.game.game_state.GameState._track_action_gain`
    (around line 1332) and fires once per turn the first time the
    player has three or more action gains while a Cauldron is in play.

    Cauldron is a *treasure*, so it lands in play during the treasure
    phase. The cleanest reliable trigger paths on this board are:

      * Workshop play (gains an action in the action phase, +1 to the
        counter) followed by 2 action buys in the buy phase (+2 to the
        counter, Cauldron in play) = 3 action gains -> trigger.
      * Hamlet's optional discard-for-+Buy + Cauldron's +1 Buy + base
        +1 Buy = 3 buys per turn. Three action buys at $2-$3 each
        ($6-$9 total) also fires the trigger.

    Greening matters as much as the curse trigger - Big Money on this
    board hits 5+ Provinces fast. The strategy below is therefore a
    Big-Money + Smithy frame with a small Cauldron + Workshop + Hamlet
    payload bolted on. That keeps the deck lean enough to hit $5-$8
    buy turns reliably while still firing the curse trigger when the
    payload pieces collide.

Strategy outline:
    * Open Cauldron + Silver (3/4) or Silver + Workshop (5/2) - the
      strategy auto-picks based on hand value.
    * Add a second Cauldron, two Smithies, one Workshop, and one
      Hamlet. Silver/Gold for income.
    * Use ``PriorityRule.card_in_play("Cauldron")`` to gate "buy any
      cheap action" rules during the buy phase.
    * Greening: Province at $8, Duchy at $5 when provinces are low,
      Mill as a $4 action-victory pile-out option in the closing
      phase.
"""

from .base_strategy import BaseStrategy, PriorityRule
from dominion.strategy.enhanced_strategy import EnhancedStrategy


class CauldronCurseStrategy(BaseStrategy):
    """Cauldron-curse seed strategy for the cauldron_curse board."""

    def __init__(self):
        super().__init__()
        self.name = "CauldronCurse"
        self.description = (
            "Hand-tuned Cauldron-curse strategy: Big-Money + Smithy frame "
            "with a Cauldron + Workshop + Hamlet payload that fires the "
            "third-action curse trigger when the pieces collide."
        )
        self.version = "1.0"

        # Helpers -----------------------------------------------------------
        cauldron_in_play = PriorityRule.card_in_play("Cauldron")

        def cauldron_payload(card_name: str, cap: int):
            """Buy *card_name* up to *cap* copies, but only when Cauldron
            is in play (i.e. during the buy phase) - this is the
            curse-trigger payload that the brief asks us to gate on
            ``PriorityRule.card_in_play("Cauldron")``."""
            return PriorityRule.and_(
                cauldron_in_play,
                PriorityRule.max_in_deck(card_name, cap),
            )

        # === GAIN PRIORITIES ===
        self.gain_priority = [
            # --- Greening (always wins when affordable) -------------------
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule(
                "Mill",
                PriorityRule.and_(
                    PriorityRule.provinces_left("<=", 4),
                    PriorityRule.max_in_deck("Mill", 3),
                ),
            ),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),

            # --- Cauldron core (the keystone) -----------------------------
            # Get one immediately, second copy soon for consistency.
            PriorityRule("Cauldron", PriorityRule.max_in_deck("Cauldron", 2)),

            # --- Gold (great after Cauldron is online) --------------------
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),

            # --- Smithy economy -----------------------------------------
            # +3 Cards is the strongest non-treasure card on this board.
            # Two copies in a 25-card deck means roughly one Smithy in
            # hand every shuffle.
            PriorityRule(
                "Smithy",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Smithy", 2),
                    PriorityRule.turn_number(">=", 2),
                ),
            ),

            # --- Curse-trigger payload (small, targeted) ------------------
            # One Workshop + one Hamlet is enough to fire the trigger
            # when the pieces collide in the same hand, but not so many
            # that the deck dilutes.
            PriorityRule("Workshop", PriorityRule.max_in_deck("Workshop", 1)),
            PriorityRule("Hamlet", PriorityRule.max_in_deck("Hamlet", 1)),

            # --- Cauldron-gated extras ("buy any cheap action") -----------
            # When Cauldron is in play (during the buy phase) any extra
            # cheap action is potentially the third action gain that
            # fires the trigger.  Hard-cap so we don't drown the deck.
            PriorityRule("Workshop", cauldron_payload("Workshop", 2)),
            PriorityRule("Hamlet",   cauldron_payload("Hamlet", 2)),
            PriorityRule("Settlers", cauldron_payload("Settlers", 2)),
            PriorityRule("Pawn",     cauldron_payload("Pawn", 1)),

            # --- Late-game economy ---------------------------------------
            # Baker is a $5 cantrip with a coin token.
            PriorityRule(
                "Baker",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Baker", 1),
                    PriorityRule.turn_number(">=", 6),
                ),
            ),
            # Silver early/mid for economy.
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.provinces_left(">", 2),
                    PriorityRule.max_in_deck("Silver", 5),
                ),
            ),
            # Settlers / Wishing Well as last-resort cantrips with extra
            # leftover coins (e.g. $2 with no other use).
            PriorityRule("Settlers",     PriorityRule.max_in_deck("Settlers", 1)),
            PriorityRule("Wishing Well", PriorityRule.max_in_deck("Wishing Well", 1)),
        ]

        # === ACTION PRIORITIES ===
        # Lead with non-terminals so Workshop and Smithy can still be
        # played afterward. Workshop's play is the action-gain that
        # banks the first count of the turn before Cauldron lands.
        self.action_priority = [
            PriorityRule("Hamlet"),
            PriorityRule("Wishing Well"),
            PriorityRule("Settlers"),
            PriorityRule("Baker"),
            PriorityRule("Pawn"),
            PriorityRule("Workshop"),
            PriorityRule("Mill"),
            PriorityRule("Smithy"),
            PriorityRule("Village"),
        ]

        # === TREASURE PRIORITIES ===
        # Cauldron first so it is in play during the buy phase, which
        # is when the curse trigger checks if any Cauldron is in play.
        self.treasure_priority = [
            PriorityRule("Cauldron"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        # === TRASH PRIORITIES ===
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule(
                "Copper",
                PriorityRule.and_(
                    PriorityRule.has_cards(["Silver", "Gold"], 3),
                    PriorityRule.turn_number("<", 12),
                ),
            ),
        ]


def create_cauldron_curse() -> EnhancedStrategy:
    """Factory function for the Cauldron-curse seed strategy."""
    return CauldronCurseStrategy()
