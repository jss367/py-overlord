"""Best-found strategy for ``boards/black_cat_and_livery.txt``.

The search converged on a compact money-and-attack deck rather than the
board's more elaborate Livery, Cavalry, or Way of the Ox engines.  It opens
with at most one early Bounty Hunter, repeatedly buys Stockpiles, adds Gold,
and fills low-value buys with as many as eight Black Cats.  Once only two
Provinces remain it adds Duchies.

Black Cat is the decisive payload.  Keeping several copies cycling through
the deck makes it likely that one or more are in hand when the opponent gains
a Victory card, handing out Curses while the Stockpile battery supplies the
money and buys needed to finish the game.

This is the curated form of the local-search variant called ``X7``.  Dead
rules for cards it never gains were removed without changing its play on the
target board.  In the final 1,000-game-per-matchup tournament, X7 beat all
five comparison variants and averaged a 59.5% win rate.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class BlackCatStockpileBestFound(EnhancedStrategy):
    """Early Bounty Hunter into Stockpile money and Black Cat attacks."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Black Cat Stockpile Best Found"
        self.description = (
            "Best-found strategy for the Black Cat and Livery board: open one "
            "early Bounty Hunter, build a Stockpile battery, buy up to eight "
            "Black Cats, and add Duchies when two Provinces remain."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule(
                "Bounty Hunter",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Bounty Hunter", 1),
                    PriorityRule.turn_number("<=", 2),
                ),
            ),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Stockpile"),
            PriorityRule("Gold"),
            PriorityRule(
                "Black Cat", PriorityRule.max_in_deck("Black Cat", 8)
            ),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            PriorityRule("Bounty Hunter"),
            PriorityRule("Black Cat"),
        ]

        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
            PriorityRule("Stockpile"),
        ]


def create_black_cat_stockpile_best_found() -> EnhancedStrategy:
    return BlackCatStockpileBestFound()
