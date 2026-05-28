"""Island seed: Investment Colony Rush for the Lisbon Colony board.

Theory of victory
-----------------
On the Lisbon kingdom (Watchtower, Clerk, Gardens, Investment, Workers'
Village, City, Collection, Festival, Expand, Peddler) the dominant
"engine" archetypes ignore Investment's other half: trash-this-for-VP.
A small pile of Investments can convert distinct treasures into a fat
VP-token pile while accelerating Colony purchases. Pair with Watchtower
so Gold/Platinum/Colony gains topdeck.

Plan
----
- Open Investment + Silver.
- Buy a few Investments early. Each turn, Investment trashes a Copper
  or Estate from hand and then takes +$1 to bridge to Gold/Platinum.
- Once we have 4-5 distinct Treasure names in hand, detonate an
  Investment: trash it, score +5 VP tokens, repeat.
- Watchtower reactions topdeck Gold/Platinum/Province/Colony into the
  next hand, so the Investment-detonation hands stay strong.

Why this is on the panel
------------------------
The City Pile Engine docstring claims "City pile-out" is the dominant
play. If a simple Investment rush is anywhere near competitive, that
claim is wrong. This seed is the falsifier.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class LisbonInvestmentRush(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Lisbon Investment Rush"
        self.description = (
            "Investment-detonation Colony rush with Watchtower topdeck "
            "reactions. No engine — just trash junk for VP and buy Colonies."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("Platinum"),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold"),
            PriorityRule("Investment", PriorityRule.max_in_deck("Investment", 5)),
            PriorityRule("Watchtower", PriorityRule.max_in_deck("Watchtower", 1)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 10)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            PriorityRule("Watchtower"),
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
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 2)),
        ]


def create_lisbon_investment_rush() -> EnhancedStrategy:
    return LisbonInvestmentRush()
