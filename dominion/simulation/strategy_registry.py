from typing import Dict, Type

from strategies.base_strategy import BaseStrategy
from strategies.big_money import BigMoneyStrategy
from strategies.chapel_witch import ChapelWitchStrategy
from strategies.village_smithy_lab import VillageSmithyLabStrategy


class StrategyRegistry:
    """Central registry for all available strategies"""

    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._register_core_strategies()

    def _register_core_strategies(self):
        """Register the core set of strategies"""
        self.register_strategy("BigMoney", BigMoneyStrategy)
        self.register_strategy("ChapelWitch", ChapelWitchStrategy)
        self.register_strategy("VillageSmithyLab", VillageSmithyLabStrategy)

    def register_strategy(self, name: str, strategy_class: Type[BaseStrategy]):
        """Register a new strategy class"""
        self._strategies[name] = strategy_class

    def get_strategy(self, name: str) -> BaseStrategy:
        """Get a new instance of a strategy by name"""
        if name not in self._strategies:
            raise ValueError(f"Unknown strategy: {name}")
        return self._strategies[name]()

    def list_strategies(self) -> list[str]:
        """Get list of all registered strategy names"""
        return list(self._strategies.keys())

    def create_strategy(self, name: str) -> BaseStrategy:
        """Create a new instance of a strategy"""
        return self.get_strategy(name)
