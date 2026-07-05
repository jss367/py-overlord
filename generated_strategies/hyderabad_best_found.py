"""Best-found strategy for ``boards/hyderabad.txt``.

Kingdom: Ducat, Scrap, Stockpile, Patron, Priest, River Shrine, Village
Green, Rice Broker, Scepter, Scholar — with the Silos project, Way of the
Otter, and the Progress prophecy pinned.

This file publishes the strongest policy found in the Hyderabad search:
the island-evolved Otter Broker champion plus one hand-found refinement
(buy Estates once two supply piles are empty, to win the three-pile
race). The evolved champion carried dead rules for cards this plan never
buys (Village Green, Priest, Rice Broker way/trash rules); those are
omitted here, matching the Lisbon Best Found precedent.

The plan is disciplined Stockpile money: Province always, exactly one
early Scholar for draw, a battery of up to six Stockpiles (each play
Exiles it; each new Stockpile gain recalls the whole battery), Gold over
mid-game green — Progress topdecks every gain, so early Duchies clog the
next hand — and a late pivot to Duchy plus pile-out Estates.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class HyderabadBestFound(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Hyderabad Best Found"
        self.description = (
            "Best-found Hyderabad board policy: Stockpile-battery money "
            "with one Scholar, late Duchies, and three-pile Estate closing."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Estate", PriorityRule.empty_piles(">=", 2)),
            PriorityRule("Gold"),
            PriorityRule(
                "Scholar",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Scholar", 1),
                    PriorityRule.turn_number("<=", 12),
                ),
            ),
            PriorityRule("Stockpile", PriorityRule.max_in_deck("Stockpile", 6)),
            PriorityRule(
                "Ducat",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Ducat", 1),
                    PriorityRule.provinces_left(">", 3),
                ),
            ),
            PriorityRule("Silver"),
        ]

        self.action_priority = [
            PriorityRule("Scholar"),
        ]

        # The evolved champion played Stockpile and Ducat via the
        # unexpected-treasure fallback; they are listed explicitly here.
        # Play order between treasures is immaterial on this board.
        self.treasure_priority = [
            PriorityRule("Silver"),
            PriorityRule("Gold"),
            PriorityRule("Copper"),
            PriorityRule("Stockpile"),
            PriorityRule("Ducat"),
        ]


def create_hyderabad_best_found() -> EnhancedStrategy:
    return HyderabadBestFound()
