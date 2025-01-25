from typing import Dict, List, Optional
import random

from dominion.cards.base_card import Card, CardType
from dominion.game.game_state import GameState
from dominion.cards.registry import get_card
from dominion.game.player_state import PlayerState

class Strategy:
    """Represents a learnable strategy."""
    def __init__(self):
        # Card priorities
        self.gain_priorities: Dict[str, float] = {}  # Priority for gaining each card
        self.play_priorities: Dict[str, float] = {}  # Priority for playing each card
        
        # Strategy weights
        self.action_weight = random.random()
        self.treasure_weight = random.random()
        self.victory_weight = random.random()
        self.engine_weight = random.random()

    @classmethod
    def create_random(cls, card_names: List[str]) -> 'Strategy':
        """Create a random initial strategy."""
        strategy = cls()
        
        # Set random priorities for all cards
        for name in card_names:
            strategy.gain_priorities[name] = random.random()
            strategy.play_priorities[name] = random.random()
            
        return strategy
    
    def mutate(self, mutation_rate: float):
        """Randomly modify the strategy."""
        # Mutate card priorities
        for priorities in [self.gain_priorities, self.play_priorities]:
            for card in priorities:
                if random.random() < mutation_rate:
                    priorities[card] = random.random()
        
        # Mutate weights
        if random.random() < mutation_rate:
            self.action_weight = random.random()
        if random.random() < mutation_rate:
            self.treasure_weight = random.random()
        if random.random() < mutation_rate:
            self.victory_weight = random.random()
        if random.random() < mutation_rate:
            self.engine_weight = random.random()

    @classmethod
    def crossover(cls, parent1: 'Strategy', parent2: 'Strategy') -> 'Strategy':
        """Create a new strategy by combining two parent strategies."""
        child = cls()
        
        # Crossover card priorities
        for card in parent1.gain_priorities:
            if random.random() < 0.5:
                child.gain_priorities[card] = parent1.gain_priorities[card]
            else:
                child.gain_priorities[card] = parent2.gain_priorities[card]
                
        for card in parent1.play_priorities:
            if random.random() < 0.5:
                child.play_priorities[card] = parent1.play_priorities[card]
            else:
                child.play_priorities[card] = parent2.play_priorities[card]
        
        # Crossover weights using interpolation
        t = random.random()
        child.action_weight = parent1.action_weight * t + parent2.action_weight * (1-t)
        child.treasure_weight = parent1.treasure_weight * t + parent2.treasure_weight * (1-t)
        child.victory_weight = parent1.victory_weight * t + parent2.victory_weight * (1-t)
        child.engine_weight = parent1.engine_weight * t + parent2.engine_weight * (1-t)
        
        return child
