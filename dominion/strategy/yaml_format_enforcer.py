from pathlib import Path
from typing import Any

import jsonschema
import yaml


class YAMLFormatEnforcer:
    """Enforces consistent format and structure for Dominion strategy YAML files."""

    # Updated schema without requiring 'strategy' wrapper
    STRATEGY_SCHEMA = {
        "type": "object",
        "required": ["actionPriority", "gainPriority", "treasurePriority"],
        "properties": {
            "metadata": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "version": {"type": "string"},
                },
            },
            "actionPriority": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["card"],
                    "properties": {
                        "card": {"type": "string"},
                        "priority": {"type": "number"},
                        "condition": {"type": "string"},
                    },
                },
            },
            "gainPriority": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["card"],
                    "properties": {
                        "card": {"type": "string"},
                        "priority": {"type": "number"},
                        "condition": {"type": "string"},
                    },
                },
            },
            "treasurePriority": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["card"],
                    "properties": {
                        "card": {"type": "string"},
                        "priority": {"type": "number"},
                        "condition": {"type": "string"},
                    },
                },
            },
        },
    }

    def __init__(self):
        """Initialize with standard card lists."""
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

    def validate_strategy(self, strategy_data: dict[str, Any]) -> list[str]:
        """Validate a strategy against the schema and return any errors."""
        errors = []

        # Handle both old and new format
        if "strategy" in strategy_data:
            strategy_data = strategy_data["strategy"]

        try:
            jsonschema.validate(instance=strategy_data, schema=self.STRATEGY_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            return errors

        # Rest of validation logic remains the same...
        return errors

    def format_strategy(self, strategy_data: dict[str, Any]) -> dict[str, Any]:
        """Format a strategy to ensure consistent structure and defaults."""
        # Handle old format gracefully
        if "strategy" in strategy_data:
            strategy_data = strategy_data["strategy"]

        # Ensure metadata exists with required fields
        if "metadata" not in strategy_data:
            strategy_data["metadata"] = {}

        metadata = strategy_data["metadata"]
        metadata.setdefault("name", "Unnamed Strategy")
        metadata.setdefault("description", "No description provided")
        metadata.setdefault("version", "1.0")

        # Add default priority lists if missing
        if "actionPriority" not in strategy_data:
            strategy_data["actionPriority"] = []

        if "gainPriority" not in strategy_data:
            strategy_data["gainPriority"] = []

        if "treasurePriority" not in strategy_data:
            strategy_data["treasurePriority"] = [
                {"card": card, "priority": 0.5} for card in self.standard_cards["treasures"]
            ]

        return strategy_data

    def _get_card_types(self, card_name: str) -> list[str]:
        """Helper method to determine card types."""
        if card_name in self.standard_cards["treasures"]:
            return ["treasure"]
        elif card_name in self.standard_cards["victory"]:
            return ["victory"]
        else:
            # For kingdom cards, return appropriate types
            # This is a simplified version - in practice, you might want to load this from a registry
            if card_name in ["Witch"]:
                return ["action", "attack"]
            elif card_name in ["Moat"]:
                return ["action", "reaction"]
            return ["action"]

    def enforce_file(self, filepath: Path) -> tuple[bool, list[str]]:
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
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.dump(formatted_strategy, f, sort_keys=False, allow_unicode=True)
                return True, []

            return False, errors

        except Exception as e:
            return False, [f"Error processing file: {str(e)}"]

    def enforce_directory(self, directory: Path) -> dict[str, list[str]]:
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


if __name__ == "__main__":
    main()
