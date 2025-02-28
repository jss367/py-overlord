import importlib.util
import inspect
from pathlib import Path
from typing import Callable, Dict, Optional

from dominion.strategy.enhanced_strategy import EnhancedStrategy


class StrategyLoader:
    """Handles loading and managing Dominion game strategies."""

    def __init__(self, strategies_dir: str = "strategies"):
        self.strategies_dir = Path(strategies_dir)
        self.strategies: Dict[str, Callable[[], EnhancedStrategy]] = {}
        self._load_all_strategies()

    def _load_all_strategies(self) -> None:
        """Automatically load all strategy factory functions from the strategies directory."""
        if not self.strategies_dir.exists():
            print(f"Strategies directory not found at {self.strategies_dir}")
            return

        strategy_files = [f for f in self.strategies_dir.glob('*.py') if f.stem != '__init__']

        for file_path in strategy_files:
            try:
                # Import the module
                module_name = f"strategies.{file_path.stem}"
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for strategy factory functions
                # These are functions that return EnhancedStrategy and start with 'create_'
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isfunction(obj)
                        and name.startswith('create_')
                        and inspect.signature(obj).return_annotation == EnhancedStrategy
                    ):

                        # Clean up the strategy name
                        # Remove 'create_' prefix and convert to title case
                        strategy_name = name[7:].replace('_', ' ').title()
                        self.register_strategy(strategy_name, obj)

            except Exception as e:
                print(f"Error loading strategy from {file_path}: {e}")

    def register_strategy(self, name: str, strategy_factory: Callable[[], EnhancedStrategy]) -> None:
        """Register a new strategy factory function."""
        self.strategies[name] = strategy_factory
        print(f"Registered strategy: {name}")

    def get_strategy(self, name: str) -> Optional[EnhancedStrategy]:
        """Get a new instance of a strategy by name."""
        strategy_factory = self.strategies.get(name)
        if strategy_factory is None:
            return None
        return strategy_factory()

    def list_strategies(self) -> list[str]:
        """Get list of all registered strategy names."""
        return sorted(list(self.strategies.keys()))
