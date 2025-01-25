from typing import Dict, List, Optional
import random
from dominion.cards.base_card import Card, CardType
from dominion.game.game_state import GameState
from dominion.cards.registry import get_card
from dominion.game.player_state import PlayerState
import json
import os
from typing import Dict, List, Optional
import random
from pathlib import Path

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
        
        # Add metadata
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.version: str = "1.0"
        self.creation_date: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert strategy to dictionary for serialization."""
        return {
            "metadata": {
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "creation_date": self.creation_date
            },
            "priorities": {
                "gain": self.gain_priorities,
                "play": self.play_priorities
            },
            "weights": {
                "action": self.action_weight,
                "treasure": self.treasure_weight,
                "victory": self.victory_weight,
                "engine": self.engine_weight
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Strategy':
        """Create strategy from dictionary representation."""
        strategy = cls()
        
        # Load metadata
        metadata = data.get("metadata", {})
        strategy.name = metadata.get("name")
        strategy.description = metadata.get("description")
        strategy.version = metadata.get("version", "1.0")
        strategy.creation_date = metadata.get("creation_date")
        
        # Load priorities
        priorities = data.get("priorities", {})
        strategy.gain_priorities = priorities.get("gain", {})
        strategy.play_priorities = priorities.get("play", {})
        
        # Load weights
        weights = data.get("weights", {})
        strategy.action_weight = weights.get("action", random.random())
        strategy.treasure_weight = weights.get("treasure", random.random())
        strategy.victory_weight = weights.get("victory", random.random())
        strategy.engine_weight = weights.get("engine", random.random())
        
        return strategy

    def save(self, filepath: str):
        """Save strategy to JSON file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'Strategy':
        """Load strategy from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @staticmethod
    def list_available_strategies(strategies_dir: str = "strategies") -> List[str]:
        """List all available strategy files in the strategies directory."""
        strategy_files = []
        strategies_path = Path(strategies_dir)
        
        if strategies_path.exists():
            strategy_files = [
                f.stem for f in strategies_path.glob("*.json")
                if f.is_file()
            ]
            
        return sorted(strategy_files)

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
