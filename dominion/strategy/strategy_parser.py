from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import yaml
from pathlib import Path


@dataclass
class CardPriority:
    card: str
    condition: Optional[str] = None
    priority: Optional[float] = None


@dataclass
class Phase:
    conditions: Dict[str, str]
    priorities: Dict[str, Dict[str, float]]


@dataclass
class Strategy:
    """Represents a strategy loaded from YAML"""

    name: str
    author: List[str]
    requires: List[str]
    gain_priority: List[CardPriority]
    phases: Optional[Dict[str, Phase]] = None
    conditional_rules: Optional[Dict[str, List[Dict[str, Any]]]] = None
    play_priorities: Optional[Dict[str, Dict[str, float]]] = None
    weights: Optional[Dict[str, Any]] = None
    wants_to_rebuild: Optional[Dict[str, str]] = None
    rebuild_priority: Optional[List[CardPriority]] = None
    name_vp_priority: Optional[List[CardPriority]] = None


class StrategyParser:
    """Handles loading and parsing of YAML strategy files"""

    @staticmethod
    def parse_card_priority(priority_data) -> CardPriority:
        if isinstance(priority_data, dict):
            return CardPriority(
                card=priority_data["card"],
                condition=priority_data.get("condition"),
                priority=(
                    float(priority_data["priority"])
                    if "priority" in priority_data
                    else None
                ),
            )
        return CardPriority(card=priority_data)

    @staticmethod
    def parse_phase(phase_data: Dict[str, Any]) -> Phase:
        return Phase(
            conditions=phase_data.get("conditions", {}),
            priorities=phase_data.get("priorities", {}),
        )

    @staticmethod
    def load_from_file(filepath: Path) -> Strategy:
        """Load and parse a strategy from a YAML file"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data is None:
                    raise ValueError(f"Empty or invalid YAML file: {filepath}")
        except Exception as e:
            print(f"Error loading YAML file {filepath}: {e}")
            raise

        # Handle nested structure under 'strategy' or 'strategies' key
        if "strategies" in data:
            data = data["strategies"][0]  # Take first strategy if list
        elif "strategy" in data:
            data = data["strategy"]

        # Parse gain priority - ensure we have valid data to iterate over
        gain_priority = [
            StrategyParser.parse_card_priority(p)
            for p in (data.get("gainPriority") or [])
        ]

        # Parse phases if they exist
        phases = None
        if "phases" in data:
            phases = {
                name: StrategyParser.parse_phase(phase_data)
                for name, phase_data in data["phases"].items()
            }

        # Parse rebuild priority only if it exists and is not None
        rebuild_priority = None
        if data.get("rebuildPriority"):
            rebuild_priority = [
                StrategyParser.parse_card_priority(p) for p in data["rebuildPriority"]
            ]

        # Parse VP priority only if it exists and is not None
        name_vp_priority = None
        if data.get("nameVPPriority"):
            name_vp_priority = [
                StrategyParser.parse_card_priority(p) for p in data["nameVPPriority"]
            ]

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


class StrategyLoader:
    """Manages loading and storing of strategies"""

    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}

    def load_directory(self, directory: Path) -> None:
        """Load all YAML strategy files from a directory"""
        if not directory.exists():
            print(f"Warning: Strategy directory {directory} does not exist")
            return

        for file in directory.glob("*.yaml"):
            try:
                strategy = StrategyParser.load_from_file(file)
                self.strategies[strategy.name] = strategy
            except Exception as e:
                print(f"Error loading strategy file {file}: {e}")

    def get_strategy(self, name: str) -> Strategy:
        """Get a strategy by name"""
        if name not in self.strategies:
            raise ValueError(f"Unknown strategy: {name}")
        return self.strategies[name]

    def list_strategies(self) -> List[str]:
        """List all available strategies"""
        return list(self.strategies.keys())
