
# dominion/ai/genetic_ai.py
from typing import Dict, List, Optional
import random
from .base_ai import AI
from ..cards.base_card import Card, CardType
from ..game.game_state import GameState

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

class GeneticAI(AI):
    """AI that uses a learnable strategy."""
    
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self._name = f"GeneticAI-{id(self)}"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose an action card to play."""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None
            
        # Get play values for each card
        values = [(self.get_action_value(c, state), c) for c in valid_choices]
        if not values:
            return None
            
        # Return highest value card
        return max(values)[1]

    def choose_treasure(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose a treasure card to play."""
        valid_choices = [c for c in choices if c is not None and c.is_treasure]
        if not valid_choices:
            return None
            
        # Play treasures in descending order of value
        return max(valid_choices, key=lambda c: c.stats.coins)

    def choose_buy(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose a card to buy."""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None
            
        # Get buy values for each card
        values = [(self.get_buy_value(c), c) for c in valid_choices]
        if not values:
            return None
            
        # Return highest value card
        return max(values)[1]

    def get_action_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to play this action."""
        base_value = self.strategy.play_priorities.get(card.name, 0.0)
        
        # Adjust based on card effects and strategy weights
        if card.stats.actions > 0:
            base_value += self.strategy.action_weight * card.stats.actions
        if card.stats.cards > 0:
            base_value += self.strategy.engine_weight * card.stats.cards
        if card.stats.coins > 0:
            base_value += self.strategy.treasure_weight * card.stats.coins
            
        return base_value

    def get_buy_value(self, card: Card) -> float:
        """Calculate how valuable it is to buy this card."""
        return self.strategy.gain_priorities.get(card.name, 0.0)
