from .base_strategy import BaseStrategy, PriorityRule


class BigMoneyStrategy(BaseStrategy):
    """Basic Big Money strategy implementation"""

    def __init__(self):
        super().__init__()
        self.name = "BigMoney"
        self.description = "Basic Big Money strategy"
        self.version = "1.0"

        # Define gain priorities
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        # Define treasure priorities
        self.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]


from dominion.strategy.enhanced_strategy import EnhancedStrategy


def create_big_money() -> EnhancedStrategy:
    return BigMoneyStrategy()
