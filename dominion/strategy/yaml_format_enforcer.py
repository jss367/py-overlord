from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema
import yaml


class YAMLFormatEnforcer:
    """Enforces consistent format and structure for Dominion strategy YAML files."""

    # Schema definition matching actual code usage
    STRATEGY_SCHEMA = {
        "type": "object",
        "required": ["strategy"],
        "properties": {
            "strategy": {
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
                    "trashPriority": {
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
        """Validate condition string syntax."""
        if not condition:
            return True

        # List of valid variable prefixes
        valid_prefixes = ["my.", "state."]

        # List of valid function calls
        valid_functions = [
            "countInDeck",
            "countInHand",
            "turn_number",
            "provinces_left",
            "countInSupply",
        ]

        try:
            # Check for valid prefixes
            has_valid_prefix = any(condition.startswith(prefix) for prefix in valid_prefixes)
            if not has_valid_prefix and not any(op in condition for op in ["<=", ">=", "<", ">", "=="]):
                return False

            # Check for valid function calls
            if "(" in condition:
                function_name = condition.split("(")[0].split(".")[-1]
                if function_name not in valid_functions:
                    return False

            return True
        except:
            return False

    def validate_strategy(self, strategy_data: dict[str, Any]) -> list[str]:
        """Validate a strategy against the schema and return any errors."""
        errors = []

        try:
            jsonschema.validate(instance=strategy_data, schema=self.STRATEGY_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            return errors

        strategy = strategy_data["strategy"]
        all_valid_cards = (
            self.standard_cards["treasures"] + self.standard_cards["victory"] + self.standard_cards["kingdom"]
        )

        # Validate each priority list
        priority_lists = {
            "actionPriority": self.standard_cards["kingdom"],
            "gainPriority": all_valid_cards,
            "treasurePriority": self.standard_cards["treasures"],
            "trashPriority": all_valid_cards,
        }

        for list_name, valid_cards in priority_lists.items():
            if list_name in strategy:
                for priority in strategy[list_name]:
                    # Validate card name
                    if priority["card"] not in valid_cards:
                        errors.append(f"Invalid card in {list_name}: {priority['card']}")

                    # Validate priority value if present
                    if "priority" in priority:
                        if not isinstance(priority["priority"], (int, float)) or not 0 <= priority["priority"] <= 1:
                            errors.append(f"Priority value for {priority['card']} must be between 0 and 1")

                    # Validate condition if present
                    if "condition" in priority:
                        if not self.validate_condition(priority["condition"]):
                            errors.append(f"Invalid condition in {list_name}: {priority['condition']}")

        return errors

    def format_strategy(self, strategy_data: dict[str, Any]) -> dict[str, Any]:
        """Format a strategy to ensure consistent structure and defaults."""
        if "strategy" not in strategy_data:
            strategy_data = {"strategy": strategy_data}

        strategy = strategy_data["strategy"]

        # Ensure metadata exists with required fields
        if "metadata" not in strategy:
            strategy["metadata"] = {}

        metadata = strategy["metadata"]
        metadata.setdefault("name", "Unnamed Strategy")
        metadata.setdefault("description", "No description provided")
        metadata.setdefault("version", "1.0")

        # Ensure all priority lists exist with default values
        if "actionPriority" not in strategy:
            strategy["actionPriority"] = [
                {"card": card, "priority": 0.5}
                for card in self.standard_cards["kingdom"]
                if any(t in ["action", "attack", "reaction"] for t in self._get_card_types(card))
            ]

        if "gainPriority" not in strategy:
            strategy["gainPriority"] = [
                {"card": card, "priority": 0.5}
                for card in (
                    self.standard_cards["treasures"] + self.standard_cards["victory"] + self.standard_cards["kingdom"]
                )
            ]

        if "treasurePriority" not in strategy:
            strategy["treasurePriority"] = [
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
