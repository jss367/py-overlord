import importlib.util
import inspect
from pathlib import Path
from typing import Callable, Dict, Optional

from dominion.strategy.enhanced_strategy import EnhancedStrategy


class StrategyLoader:
    """Handles loading and managing Dominion game strategies."""

    def __init__(self, strategies_dir: Optional[str] = None):
        if strategies_dir is None:
            self.strategies_dir = Path(__file__).parent / "strategies"
        else:
            self.strategies_dir = Path(strategies_dir)
        self.strategies: Dict[str, Callable[[], EnhancedStrategy]] = {}
        # Track the *display* names we want to show to users (spaces, title-case)
        self._display_names: set[str] = set()
        self._load_all_strategies()

    @staticmethod
    def _slugify(name: str) -> str:
        """Return a CLI-friendly identifier for *name* (lowercase, no spaces)."""
        # Replace spaces and dashes with underscores then lowercase.
        return name.replace("-", " ").replace("_", " ").lower().replace(" ", "_")

    def _load_all_strategies(self) -> None:
        """Automatically load all strategy factory functions from the strategies directory."""
        if not self.strategies_dir.exists():
            print(f"Strategies directory not found at {self.strategies_dir}")
            return

        strategy_files = [f for f in self.strategies_dir.glob('*.py') if f.stem != '__init__']

        for file_path in strategy_files:
            try:
                # Import the module
                module_name = f"dominion.strategy.strategies.{file_path.stem}"
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
                        # Remove 'create_' prefix and convert to title case with spaces
                        strategy_name = name[7:].replace('_', ' ').title()
                        self.register_strategy(strategy_name, obj)

            except Exception as e:
                print(f"Error loading strategy from {file_path}: {e}")

    def register_strategy(self, name: str, strategy_factory: Callable[[], EnhancedStrategy]) -> None:
        """Register a new strategy factory function.

        Besides the human-readable *name* (e.g. "Big Money") we also create
        alias keys that are easier to type on the command line (e.g.
        "big_money", "big-money", "bigmoney"). All aliases point to the same
        factory, so users can choose whichever they prefer.
        """
        # Primary display name (kept as provided)
        self.strategies[name] = strategy_factory
        self._display_names.add(name)

        # Generate and register aliases ---------------------------------
        slug = self._slugify(name)  # big_money
        mini_slug = slug.replace("_", "")  # bigmoney
        dash_slug = slug.replace("_", "-")  # big-money

        for alias in {slug, mini_slug, dash_slug, name.lower()}:
            # Do not overwrite an existing mapping if one is already present
            self.strategies.setdefault(alias, strategy_factory)

        # Print registration information (optional for debugging)
        print(f"Registered strategy: {name} (aliases: {', '.join({slug, dash_slug})})")

    def get_strategy(self, name: str) -> Optional[EnhancedStrategy]:
        """Get a new instance of a strategy by name or any of its aliases."""
        # Try exact match first, then case-insensitive, then slugify attempt.
        strategy_factory = self.strategies.get(name)
        if strategy_factory is None:
            strategy_factory = self.strategies.get(name.lower())
        if strategy_factory is None:
            strategy_factory = self.strategies.get(self._slugify(name))
        if strategy_factory is None:
            return None
        return strategy_factory()

    def list_strategies(self) -> list[str]:
        """Return display names only (deduplicated, sorted)."""
        return sorted(self._display_names)
