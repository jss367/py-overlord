# dominion/ai/base_ai.py
from abc import ABC, abstractmethod
from typing import List, Optional
from ..cards.base_card import Card
from ..game.game_state import GameState

class AI(ABC):
    """Base class for all AIs."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @abstractmethod
    def choose_action(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose an action to play from available choices."""
        pass
        
    @abstractmethod
    def choose_treasure(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose a treasure to play from available choices."""
        pass
        
    @abstractmethod
    def choose_buy(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose a card to buy from available choices."""
        pass