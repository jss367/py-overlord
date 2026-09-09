"""Best strategy found for the base-set First Game board.

Board: ``boards/calibration/first_game.txt`` (Cellar, Market, Merchant,
Militia, Mine, Moat, Remodel, Smithy, Village, Workshop).

The hand search in ``scripts/search_first_game.py`` ranked money variants in a
paired-seat round robin. Militia money beat Smithy money outright, Markets on
top of Militia money added another ~15 points, and every engine, Remodel,
Merchant, Mine, Workshop and Cellar variant lost to the money line. See the
"First Game Strategy Search Guide" in the strategy catalog for the numbers.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class FirstGameMilitiaMarket(EnhancedStrategy):
    """Big Money with up to three Militias and three Markets, no Smithy."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "First Game Militia Market"
        self.description = (
            "Money with three Militias and three Markets on the First Game kingdom; "
            "beats Smithy/Militia money about 72% head-to-head."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Gold"),
            PriorityRule("Market", PriorityRule.max_in_deck("Market", 3)),
            PriorityRule("Militia", PriorityRule.max_in_deck("Militia", 3)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Market"),
            PriorityRule("Militia"),
        ]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_first_game_militia_market() -> EnhancedStrategy:
    return FirstGameMilitiaMarket()
