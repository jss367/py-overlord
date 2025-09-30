from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategies.base_strategy import BaseStrategy, PriorityRule


class BigMoneySmithyStrategy(BaseStrategy):
    """Big Money strategy that adds Smithy for extra draw."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "BigMoneySmithy"
        self.description = "Big Money strategy with Smithy support"
        self.version = "2.0"

        self.gain_priority = []

        # Always play Smithy when available
        self.action_priority = [PriorityRule("Smithy")]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

    # ------------------------------------------------------------------
    def choose_gain(self, state, player, choices):
        """Dynamically choose a card to buy based on available coins."""
        card_lookup = {c.name: c for c in choices if c is not None}
        money = player.coins

        if money >= 8 and "Province" in card_lookup:
            return card_lookup["Province"]
        if money >= 6 and "Gold" in card_lookup:
            return card_lookup["Gold"]
        if money == 4 and "Smithy" in card_lookup:
            return card_lookup["Smithy"]
        if money >= 3 and "Silver" in card_lookup:
            return card_lookup["Silver"]

        return None


def create_big_money_smithy() -> EnhancedStrategy:
    return BigMoneySmithyStrategy()
