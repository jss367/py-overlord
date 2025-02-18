import importlib.util
import inspect
from pathlib import Path
from typing import Optional, Type

from dominion.strategy.enhanced_strategy import EnhancedStrategy as BaseStrategy


class StrategyLoader:
    """Handles loading and managing Dominion game strategies."""

    def __init__(self):
        self.strategies: dict[str, Type[BaseStrategy]] = {}
        self._load_all_strategies()

    def _load_all_strategies(self) -> None:
        """Automatically load all strategy classes from the strategies directory."""
        # Get the strategies directory within the strategy package
        strategies_dir = Path(__file__).parent / 'strategies'

        if not strategies_dir.exists():
            print(f"Strategies directory not found at {strategies_dir}")
            return

        # Get all Python files in the strategies directory
        strategy_files = [f for f in strategies_dir.glob('*.py') if f.stem != '__init__']

        for file_path in strategy_files:
            try:
                # Create the module name in the correct package
                module_name = f"dominion.strategy.strategies.{file_path.stem}"

                # Load module using file path
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    print(f"Could not load spec for {file_path}")
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find all strategy classes in the module
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BaseStrategy) and obj != BaseStrategy:
                        self.register_strategy(obj.__name__, obj)

            except Exception as e:
                print(f"Error loading strategy from {file_path}: {e}")

    def register_strategy(self, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """Register a new strategy class."""
        self.strategies[name] = strategy_class
        print(f"Registered strategy: {name}")

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get a new instance of a strategy by name."""
        strategy_class = self.strategies.get(name)
        if strategy_class is None:
            return None
        return strategy_class()

    def list_strategies(self) -> list[str]:
        """Get list of all registered strategy names."""
        return list(self.strategies.keys())

    def clear_strategies(self) -> None:
        """Clear all registered strategies and reload them."""
        self.strategies.clear()
        self._load_all_strategies()
