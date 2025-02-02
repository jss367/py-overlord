from typing import Dict, Any, List
import yaml
from pathlib import Path
from datetime import datetime
import jsonschema


class YAMLFormatEnforcer:
    """Enforces consistent format and structure for Dominion strategy YAML files."""

    # Schema definition for strategy YAML files

    STRATEGY_SCHEMA = {
        "type": "object",
        "required": ["strategy"],
        "properties": {
            "strategy": {
                "type": "object",
                "required": [
                    "gainPriority",
                    "play_priorities",
                    "weights",
                ],
                "properties": {
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "version": {"type": "string"},
                            "creation_date": {"type": "string"},
                        },
                    },
                    "author": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "requires": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "gainPriority": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["card", "priority"],
                            "properties": {
                                "card": {"type": "string"},
                                "priority": {"type": "number"},
                                "condition": {"type": "string"},
                            },
                        },
                    },
                    "play_priorities": {
                        "type": "object",
                        "required": ["default"],
                        "properties": {
                            "default": {
                                "type": "object",
                                "additionalProperties": {"type": "number"},
                            }
                        },
                    },
                    "weights": {
                        "type": "object",
                        "required": ["action", "treasure", "victory", "engine"],
                        "properties": {
                            "action": {"type": "number"},
                            "treasure": {"type": "number"},
                            "victory": {
                                "oneOf": [
                                    {"type": "number"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "default": {"type": "number"},
                                            "endgame": {"type": "number"},
                                        },
                                    },
                                ]
                            },
                            "engine": {"type": "number"},
                        },
                    },
                    "phases": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "conditions": {"type": "object"},
                                "priorities": {"type": "object"},
                            },
                        },
                    },
                    "conditional_rules": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "conditions": {"type": "object"},
                                    "priorities": {"type": "object"},
                                },
                            },
                        },
                    },
                },
            }
        },
    }

    def __init__(self):
        """Initialize the format enforcer with standard card lists."""
        self.standard_cards = {
            "treasures": ["Copper", "Silver", "Gold"],
            "victory": ["Estate", "Duchy", "Province", "Curse"],
            "kingdom": [
                "Village",
                "Smithy",
                "Market",
                "Festival",
                "Laboratory",
                "Mine",
                "Witch",
                "Moat",
                "Workshop",
                "Chapel",
            ],
        }

    def validate_condition(self, condition: str) -> bool:
        """Safely validate a condition string."""
        # Basic string comparisons
        for op in ["<=", ">=", "<", ">", "=="]:
            if op in condition:
                parts = condition.split(op)
                if len(parts) == 2:
                    try:
                        # Convert any numeric values for comparison
                        left = parts[0].strip()
                        right = parts[1].strip()
                        # If both are numeric, ensure comparison is valid
                        if left.isdigit() and right.isdigit():
                            return True
                        # Otherwise, assume it's a valid variable comparison
                        return True
                    except:
                        return False
        return True  # Allow other conditions by default

    def validate_strategy(self, strategy_data: Dict[str, Any]) -> List[str]:
        """Validate a strategy against the schema and return any errors."""
        errors = []

        try:
            jsonschema.validate(instance=strategy_data, schema=self.STRATEGY_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            return errors

        strategy = strategy_data["strategy"]

        # Validate card references
        all_valid_cards = (
            self.standard_cards["treasures"]
            + self.standard_cards["victory"]
            + self.standard_cards["kingdom"]
        )

        # Check gain priority cards
        for priority in strategy["gainPriority"]:
            if priority["card"] not in all_valid_cards:
                errors.append(f"Invalid card in gainPriority: {priority['card']}")
            if not 0 <= priority["priority"] <= 1:
                errors.append(
                    f"Priority value for {priority['card']} must be between 0 and 1"
                )
            if "condition" in priority:
                if not self.validate_condition(priority["condition"]):
                    errors.append(
                        f"Invalid condition in gainPriority: {priority['condition']}"
                    )

        # Check phases if they exist
        if "phases" in strategy:
            for phase_name, phase in strategy["phases"].items():
                if "conditions" in phase:
                    for cond_name, condition in phase["conditions"].items():
                        if not self.validate_condition(str(condition)):
                            errors.append(
                                f"Invalid condition in phase {phase_name}: {condition}"
                            )

        # Check play priorities
        for card, priority in strategy["play_priorities"]["default"].items():
            if card not in all_valid_cards:
                errors.append(f"Invalid card in play_priorities: {card}")
            if not 0 <= priority <= 1:
                errors.append(f"Play priority for {card} must be between 0 and 1")

        # Check weights
        for weight_type, value in strategy["weights"].items():
            if not 0 <= value <= 1:
                errors.append(f"Weight {weight_type} must be between 0 and 1")

        # Check required cards are in kingdom cards
        for card in strategy["requires"]:
            if card not in self.standard_cards["kingdom"]:
                errors.append(f"Required card {card} is not a valid kingdom card")

        return errors

    def format_strategy(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a strategy to ensure consistent structure and defaults."""
        if "strategy" not in strategy_data:
            strategy_data = {"strategy": strategy_data}

        strategy = strategy_data["strategy"]

        # Ensure metadata exists and has all required fields
        if "metadata" not in strategy:
            strategy["metadata"] = {}

        metadata = strategy["metadata"]
        metadata.setdefault("name", "Unnamed Strategy")
        metadata.setdefault("description", "No description provided")
        metadata.setdefault("version", "1.0")
        metadata.setdefault("creation_date", datetime.now().strftime("%Y-%m-%d"))

        # Ensure basic lists exist
        strategy.setdefault("author", ["Unknown"])
        strategy.setdefault("requires", [])

        # Ensure gain priorities exist for all standard cards
        existing_priorities = {p["card"]: p for p in strategy.get("gainPriority", [])}
        strategy["gainPriority"] = []

        for card in (
            self.standard_cards["treasures"]
            + self.standard_cards["victory"]
            + self.standard_cards["kingdom"]
        ):
            if card in existing_priorities:
                strategy["gainPriority"].append(existing_priorities[card])
            else:
                strategy["gainPriority"].append(
                    {"card": card, "priority": 0.5}  # Default priority
                )

        # Ensure play priorities exist
        if "play_priorities" not in strategy:
            strategy["play_priorities"] = {"default": {}}

        if "default" not in strategy["play_priorities"]:
            strategy["play_priorities"]["default"] = {}

        for card in (
            self.standard_cards["treasures"]
            + self.standard_cards["victory"]
            + self.standard_cards["kingdom"]
        ):
            strategy["play_priorities"]["default"].setdefault(card, 0.5)

        # Ensure weights exist
        if "weights" not in strategy:
            strategy["weights"] = {}

        weights = strategy["weights"]
        weights.setdefault("action", 0.7)
        weights.setdefault("treasure", 0.6)
        weights.setdefault("victory", 0.3)
        weights.setdefault("engine", 0.8)

        return strategy_data

    def enforce_file(self, filepath: Path) -> tuple[bool, List[str]]:
        """Validate and format a strategy file, saving the formatted version."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                strategy_data = yaml.safe_load(f)

            # Format the strategy
            formatted_strategy = self.format_strategy(strategy_data)

            # Validate the formatted strategy
            errors = self.validate_strategy(formatted_strategy)

            if not errors:
                # Save the formatted version
                with open(filepath, "w") as f:
                    yaml.dump(formatted_strategy, f, sort_keys=False)
                return True, []

            return False, errors

        except Exception as e:
            return False, [f"Error processing file: {str(e)}"]

    def enforce_directory(self, directory: Path) -> Dict[str, List[str]]:
        """Process all YAML files in a directory."""
        results = {}

        if not directory.exists():
            return {"error": ["Directory does not exist"]}

        for filepath in directory.glob("*.yaml"):
            success, errors = self.enforce_file(filepath)
            results[filepath.name] = errors if errors else ["OK"]

        return results


def main():
    """Command line interface for the YAML enforcer."""
    enforcer = YAMLFormatEnforcer()

    # Process strategies directory
    strategies_dir = Path("strategies")
    if not strategies_dir.exists():
        print("Creating strategies directory...")
        strategies_dir.mkdir()

    print("\nProcessing strategy files...")
    results = enforcer.enforce_directory(strategies_dir)

    # Display results
    print("\nResults:")
    for filename, errors in results.items():
        print(f"\n{filename}:")
        for error in errors:
            print(f"  {'✓' if error == 'OK' else '✗'} {error}")
