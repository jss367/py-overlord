from pathlib import Path
from typing import Optional

import yaml

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class StrategyLoader:
    """Handles loading and managing Dominion game strategies from YAML files."""

    def __init__(self):
        self.strategies: dict[str, EnhancedStrategy] = {}

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
            with open(file_path, 'r', encoding='utf-8') as f:
                strategy_data = yaml.safe_load(f)

            if not isinstance(strategy_data, dict):
                raise ValueError(f"Invalid strategy format in {file_path}")

            # Handle both old format with 'strategy' wrapper and new direct format
            if 'strategy' in strategy_data:
                strategy_data = strategy_data['strategy']

            # Create new strategy
            strategy = EnhancedStrategy()

            # Set metadata
            if 'metadata' in strategy_data:
                strategy.name = strategy_data['metadata'].get('name', file_path.stem)

            # Convert action priorities
            if 'actionPriority' in strategy_data:
                strategy.action_priority = [
                    PriorityRule(
                        card_name=rule['card'] if isinstance(rule, dict) else rule,
                        condition=rule.get('condition') if isinstance(rule, dict) else None,
                    )
                    for rule in strategy_data['actionPriority']
                ]

            # Convert gain priorities
            if 'gainPriority' in strategy_data:
                strategy.gain_priority = [
                    PriorityRule(
                        card_name=rule['card'] if isinstance(rule, dict) else rule,
                        condition=rule.get('condition') if isinstance(rule, dict) else None,
                    )
                    for rule in strategy_data['gainPriority']
                ]

            # Convert treasure priorities
            if 'treasurePriority' in strategy_data:
                strategy.treasure_priority = [
                    PriorityRule(
                        card_name=rule['card'] if isinstance(rule, dict) else rule,
                        condition=rule.get('condition') if isinstance(rule, dict) else None,
                    )
                    for rule in strategy_data['treasurePriority']
                ]

            # Store strategy
            self.strategies[strategy.name] = strategy
            print(f"Successfully loaded strategy: {strategy.name}")
            return strategy

        except Exception as e:
            print(f"Error loading strategy file {file_path}: {e}")
            raise

    def get_strategy(self, name: str) -> Optional[EnhancedStrategy]:
        """Get a strategy by name."""
        return self.strategies.get(name)

    def list_strategies(self) -> list[str]:
        """Get list of all loaded strategy names."""
        return list(self.strategies.keys())
