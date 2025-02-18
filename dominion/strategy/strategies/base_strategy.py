from dataclasses import dataclass
from typing import List

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


@dataclass
class BaseStrategy(EnhancedStrategy):
    """Base class for all Python-based strategies"""

    def __init__(self):
        super().__init__()
        self.name = "Unnamed Strategy"
        self.description = "Base strategy implementation"
        self.version = "1.0"

        # Initialize empty priority lists
        self.gain_priority: List[PriorityRule] = []
        self.action_priority: List[PriorityRule] = []
        self.trash_priority: List[PriorityRule] = []
        self.treasure_priority: List[PriorityRule] = []
