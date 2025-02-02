from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from dominion.strategy.yaml_format_enforcer import YAMLFormatEnforcer


@dataclass
class CardPriority:
    card: str
    condition: Optional[str] = None
    priority: Optional[float] = None


@dataclass
class Phase:
    conditions: dict[str, str]
    priorities: dict[str, dict[str, float]]


@dataclass
class Strategy:
    """Represents a strategy loaded from YAML"""

    name: str
    author: list[str]
    requires: list[str]
    gain_priority: list[CardPriority]
    phases: Optional[dict[str, Phase]] = None
    conditional_rules: Optional[dict[str, list[dict[str, Any]]]] = None
    play_priorities: Optional[dict[str, dict[str, float]]] = None
    weights: Optional[dict[str, Any]] = None
    wants_to_rebuild: Optional[dict[str, str]] = None
    rebuild_priority: Optional[list[CardPriority]] = None
    name_vp_priority: Optional[list[CardPriority]] = None


class StrategyParser:
    """Handles loading and parsing of YAML strategy files"""

    @staticmethod
    def parse_card_priority(priority_data) -> CardPriority:
        if isinstance(priority_data, dict):
            return CardPriority(
                card=priority_data["card"],
                condition=priority_data.get("condition"),
                priority=(float(priority_data["priority"]) if "priority" in priority_data else None),
            )
        return CardPriority(card=priority_data)

    @staticmethod
    def parse_phase(phase_data: dict[str, Any]) -> Phase:
        return Phase(
            conditions=phase_data.get("conditions", {}),
            priorities=phase_data.get("priorities", {}),
        )

    @staticmethod
    def load_from_file(filepath: Path) -> Strategy:
        """Load and parse a strategy from a YAML file with validation"""
        # Create enforcer
        enforcer = YAMLFormatEnforcer()

        try:
            # Load the raw YAML
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data is None:
                    raise ValueError(f"Empty or invalid YAML file: {filepath}")

            # Validate and format the strategy
            success, errors = enforcer.enforce_file(filepath)
            if not success:
                error_msg = "\n".join(errors)
                raise ValueError(f"Invalid strategy file {filepath}:\n{error_msg}")

            # Reload the formatted file
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Handle nested structure under 'strategy' or 'strategies' key
            if "strategies" in data:
                data = data["strategies"][0]  # Take first strategy if list
            elif "strategy" in data:
                data = data["strategy"]

            # Parse gain priority
            gain_priority = [StrategyParser.parse_card_priority(p) for p in (data.get("gainPriority") or [])]

            # Parse phases if they exist
            phases = None
            if "phases" in data:
                phases = {name: StrategyParser.parse_phase(phase_data) for name, phase_data in data["phases"].items()}

            # Parse rebuild priority
            rebuild_priority = None
            if data.get("rebuildPriority"):
                rebuild_priority = [StrategyParser.parse_card_priority(p) for p in data["rebuildPriority"]]

            # Parse VP priority
            name_vp_priority = None
            if data.get("nameVPPriority"):
                name_vp_priority = [StrategyParser.parse_card_priority(p) for p in data["nameVPPriority"]]

            return Strategy(
                name=data.get("metadata", {}).get("name", data.get("name", "")),
                author=data.get("author", []),
                requires=data.get("requires", []),
                gain_priority=gain_priority,
                phases=phases,
                conditional_rules=data.get("conditional_rules"),
                play_priorities=data.get("play_priorities"),
                weights=data.get("weights"),
                wants_to_rebuild=data.get("wantsToRebuild"),
                rebuild_priority=rebuild_priority,
                name_vp_priority=name_vp_priority,
            )

        except Exception as e:
            print(f"Error loading strategy file {filepath}: {e}")
            raise


class StrategyLoader:
    """Manages loading and storing of strategies"""

    def __init__(self):
        self.strategies: dict[str, Strategy] = {}
        self.enforcer = YAMLFormatEnforcer()

    def load_directory(self, directory: Path) -> None:
        """Load all YAML strategy files from a directory"""
        if not directory.exists():
            print(f"Warning: Strategy directory {directory} does not exist")
            return

        print("\nLoading strategy files...")
        for file in directory.glob("*.yaml"):
            try:
                # First validate the file
                success, errors = self.enforcer.enforce_file(file)
                if not success:
                    print(f"\nSkipping {file.name} due to validation errors:")
                    for error in errors:
                        print(f"  - {error}")
                    continue

                # If valid, load the strategy
                strategy = StrategyParser.load_from_file(file)
                self.strategies[strategy.name] = strategy
                print(f"✓ Loaded {file.name}")
            except Exception as e:
                print(f"✗ Error loading {file.name}: {e}")

    def get_strategy(self, name: str) -> Strategy:
        """Get a strategy by name"""
        if name not in self.strategies:
            raise ValueError(f"Unknown strategy: {name}")
        return self.strategies[name]

    def list_strategies(self) -> list[str]:
        """list all available strategies"""
        return list(self.strategies.keys())
