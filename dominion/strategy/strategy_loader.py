from pathlib import Path
from typing import Dict, Optional

import yaml

from dominion.strategy.enhanced_strategy import EnhancedStrategy


class StrategyLoader:
    """Handles loading and managing Dominion game strategies from YAML files."""

    def __init__(self):
        self.strategies: Dict[str, EnhancedStrategy] = {}

    def load_directory(self, directory: Path) -> None:
        """Load all YAML strategy files from a directory."""
        if not directory.exists():
            directory.mkdir(parents=True)

        # Clear existing strategies
        self.strategies.clear()

        # Load all YAML files
        for file_path in directory.glob("*.yaml"):
            try:
                self.load_file(file_path)
            except Exception as e:
                print(f"Error loading strategy from {file_path}: {e}")

    def load_file(self, file_path: Path) -> Optional[EnhancedStrategy]:
        """Load a single strategy file and return the strategy."""
        try:
            with open(file_path, 'r') as f:
                yaml_data = yaml.safe_load(f)

            # Create strategy from YAML
            strategy = EnhancedStrategy.from_yaml(yaml_data)

            # Store strategy using its name as key
            self.strategies[strategy.name] = strategy

            return strategy

        except Exception as e:
            print(f"Error loading strategy file {file_path}: {e}")
            return None

    def get_strategy(self, name: str) -> Optional[EnhancedStrategy]:
        """Get a strategy by name."""
        return self.strategies.get(name)

    def list_strategies(self) -> list[str]:
        """Get list of all loaded strategy names."""
        return list(self.strategies.keys())
