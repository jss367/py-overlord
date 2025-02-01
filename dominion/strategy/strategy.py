import json
import os
import random
from pathlib import Path


class Strategy:
    """Represents a learnable strategy."""

    def __init__(self):
        # Initialize metadata
        self.name = None
        self.description = None
        self.version = "1.0"
        self.creation_date = None

        # Initialize with smart default priorities
        self.gain_priorities = {
            # Treasures
            "Gold": 0.8,
            "Silver": 0.7,
            "Copper": -0.1,  # Negative to discourage buying
            # Victory Cards
            "Province": 0.9,
            "Duchy": 0.4,
            "Estate": -0.2,  # Negative to discourage buying
            "Curse": -1.0,  # Strong negative to never buy
            # Action Cards
            "Chapel": 0.85,  # High priority for deck thinning
            "Laboratory": 0.75,  # Card draw + action
            "Village": 0.7,  # Actions
            "Smithy": 0.65,  # Strong card draw
            "Market": 0.6,  # Good all-around
            "Festival": 0.55,  # Actions + coins
            "Mine": 0.5,  # Treasure upgrading
            "Workshop": 0.45,  # Early game gain
            "Witch": 0.7,  # Strong attack
            "Moat": 0.4,  # Reaction + cards
        }

        self.play_priorities = {
            # Treasures always played in order
            "Gold": 1.0,
            "Silver": 0.9,
            "Copper": 0.8,
            # Action Cards
            "Chapel": 1.0,  # Always play first
            "Laboratory": 0.95,
            "Village": 0.9,
            "Smithy": 0.85,
            "Market": 0.8,
            "Festival": 0.75,
            "Mine": 0.7,
            "Workshop": 0.65,
            "Witch": 0.8,
            "Moat": 0.6,
        }

        # Strategy weights
        self.action_weight = 0.7  # Favor actions for engine building
        self.treasure_weight = 0.6  # Still want treasures
        self.victory_weight = 0.3  # Lower until late game
        self.engine_weight = 0.8  # Strong focus on engine building

    @classmethod
    def create_random(cls, card_names: list[str]) -> "Strategy":
        """Create a random strategy with smart initialization."""
        strategy = cls()  # Get default priorities

        # Randomly adjust priorities within reasonable bounds
        for name in card_names:
            base_gain = strategy.gain_priorities.get(name, 0.0)
            base_play = strategy.play_priorities.get(name, 0.0)

            # Adjust gain priority ±30%
            strategy.gain_priorities[name] = max(
                -1.0, min(1.0, base_gain + (random.random() - 0.5) * 0.6)
            )

            # Adjust play priority ±20%
            strategy.play_priorities[name] = max(
                0.0, min(1.0, base_play + (random.random() - 0.5) * 0.4)
            )

        # Randomly adjust weights within reasonable bounds
        strategy.action_weight = random.uniform(0.5, 0.9)
        strategy.treasure_weight = random.uniform(0.4, 0.8)
        strategy.victory_weight = random.uniform(0.2, 0.4)
        strategy.engine_weight = random.uniform(0.6, 1.0)

        return strategy

    def mutate(self, mutation_rate: float):
        """Randomly modify the strategy with smart constraints."""
        # Mutate card priorities
        for card, current in self.gain_priorities.items():
            if random.random() < mutation_rate:
                # Adjust gain priority by up to ±20% while keeping in valid range
                change = (random.random() - 0.5) * 0.4
                self.gain_priorities[card] = max(-1.0, min(1.0, current + change))

        for card, current in self.play_priorities.items():
            if random.random() < mutation_rate:
                # Adjust play priority by up to ±15% while keeping in valid range
                change = (random.random() - 0.5) * 0.3
                self.play_priorities[card] = max(0.0, min(1.0, current + change))

        # Mutate weights with constraints
        if random.random() < mutation_rate:
            self.action_weight = max(
                0.3, min(0.9, self.action_weight + (random.random() - 0.5) * 0.4)
            )
        if random.random() < mutation_rate:
            self.treasure_weight = max(
                0.3, min(0.8, self.treasure_weight + (random.random() - 0.5) * 0.4)
            )
        if random.random() < mutation_rate:
            self.victory_weight = max(
                0.1, min(0.5, self.victory_weight + (random.random() - 0.5) * 0.3)
            )
        if random.random() < mutation_rate:
            self.engine_weight = max(
                0.4, min(1.0, self.engine_weight + (random.random() - 0.5) * 0.4)
            )

    @classmethod
    def crossover(cls, parent1: "Strategy", parent2: "Strategy") -> "Strategy":
        """Create a new strategy by combining two parent strategies."""
        child = cls()

        # Crossover card priorities using weighted average
        for card in parent1.gain_priorities:
            weight = random.random()
            child.gain_priorities[card] = parent1.gain_priorities[
                card
            ] * weight + parent2.gain_priorities[card] * (1 - weight)

        for card in parent1.play_priorities:
            weight = random.random()
            child.play_priorities[card] = parent1.play_priorities[
                card
            ] * weight + parent2.play_priorities[card] * (1 - weight)

        # Crossover weights using weighted average
        weight = random.random()
        child.action_weight = parent1.action_weight * weight + parent2.action_weight * (
            1 - weight
        )
        child.treasure_weight = (
            parent1.treasure_weight * weight + parent2.treasure_weight * (1 - weight)
        )
        child.victory_weight = (
            parent1.victory_weight * weight + parent2.victory_weight * (1 - weight)
        )
        child.engine_weight = parent1.engine_weight * weight + parent2.engine_weight * (
            1 - weight
        )

        return child

    def to_dict(self) -> dict:
        """Convert strategy to dictionary for serialization."""
        return {
            "metadata": {
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "creation_date": self.creation_date,
            },
            "priorities": {"gain": self.gain_priorities, "play": self.play_priorities},
            "weights": {
                "action": self.action_weight,
                "treasure": self.treasure_weight,
                "victory": self.victory_weight,
                "engine": self.engine_weight,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Strategy":
        """Create strategy from dictionary representation."""
        strategy = cls()  # Get default priorities first

        # Load metadata
        metadata = data.get("metadata", {})
        strategy.name = metadata.get("name")
        strategy.description = metadata.get("description")
        strategy.version = metadata.get("version", "1.0")
        strategy.creation_date = metadata.get("creation_date")

        # Load priorities, falling back to defaults if missing
        priorities = data.get("priorities", {})
        loaded_gain = priorities.get("gain", {})
        loaded_play = priorities.get("play", {})

        # Update defaults with loaded values
        strategy.gain_priorities.update(loaded_gain)
        strategy.play_priorities.update(loaded_play)

        # Load weights with defaults
        weights = data.get("weights", {})
        strategy.action_weight = weights.get("action", 0.7)
        strategy.treasure_weight = weights.get("treasure", 0.6)
        strategy.victory_weight = weights.get("victory", 0.3)
        strategy.engine_weight = weights.get("engine", 0.8)

        return strategy

    def save(self, filepath: str):
        """Save strategy to JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "Strategy":
        """Load strategy from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @staticmethod
    def list_available_strategies(strategies_dir: str = "strategies") -> list[str]:
        """List all available strategy files in the strategies directory."""
        strategy_files = []
        strategies_path = Path(strategies_dir)

        if strategies_path.exists():
            strategy_files = [
                f.stem for f in strategies_path.glob("*.json") if f.is_file()
            ]

        return sorted(strategy_files)
