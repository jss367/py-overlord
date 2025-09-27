import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml

from dominion.boards.loader import BoardConfig, load_board
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def load_kingdom_cards_from_yaml(yaml_path: str) -> tuple[list[str], dict]:
    """Load kingdom cards and optional training parameters from a YAML file."""
    try:
        with open(yaml_path, 'r') as file:
            data = yaml.safe_load(file)
            if 'kingdom_cards' not in data:
                raise ValueError("YAML file must contain 'kingdom_cards' key")

            kingdom_cards = data['kingdom_cards']
            training_params = data.get('training_parameters', {})

            return kingdom_cards, training_params
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")


def save_strategy_as_python(strategy: EnhancedStrategy, path: Path, class_name: str = "GeneratedStrategy") -> None:
    """Serialize an EnhancedStrategy as a Python module."""

    def format_list(name: str, rules: list[PriorityRule]) -> list[str]:
        lines = [f"        self.{name} = ["]
        for rule in rules:
            if rule.condition:
                lines.append(f"            PriorityRule({rule.card_name!r}, {rule.condition!r}),")
            else:
                lines.append(f"            PriorityRule({rule.card_name!r}),")
        lines.append("        ]")
        return lines

    lines = [
        "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule",
        "",
        "",
        f"class {class_name}(EnhancedStrategy):",
        "    def __init__(self) -> None:",
        "        super().__init__()",
        f"        self.name = {strategy.name!r}",
        "        self.description = \"Auto-generated strategy from genetic training\"",
        "        self.version = \"1.0\"",
        "",
    ]

    if strategy.gain_priority:
        lines.extend(format_list("gain_priority", strategy.gain_priority))
        lines.append("")
    if strategy.action_priority:
        lines.extend(format_list("action_priority", strategy.action_priority))
        lines.append("")
    if strategy.treasure_priority:
        lines.extend(format_list("treasure_priority", strategy.treasure_priority))
        lines.append("")
    if strategy.trash_priority:
        lines.extend(format_list("trash_priority", strategy.trash_priority))
        lines.append("")
    if getattr(strategy, "discard_priority", None):
        lines.extend(format_list("discard_priority", strategy.discard_priority))
        lines.append("")

    lines.extend(
        [
            f"def create_{class_name.lower()}() -> EnhancedStrategy:",
            f"    return {class_name}()",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Train a Dominion strategy using genetic algorithms")
    parser.add_argument("--kingdom-cards", nargs="+", help="List of kingdom cards to use for training")
    parser.add_argument("--config", "-c", help="YAML configuration file containing kingdom cards")
    parser.add_argument(
        "--population-size", type=int, default=5, help="Population size for genetic algorithm (default: 5)"
    )
    parser.add_argument("--generations", type=int, default=10, help="Number of generations to run (default: 10)")
    parser.add_argument("--mutation-rate", type=float, default=0.1, help="Mutation rate (default: 0.1)")
    parser.add_argument(
        "--games-per-eval", type=int, default=10, help="Number of games to play per strategy evaluation (default: 10)"
    )
    parser.add_argument("--board", help="Board definition file containing kingdom cards and landscapes")

    args = parser.parse_args()

    # Determine kingdom cards from arguments, config file, or defaults
    kingdom_cards = None
    board_config: BoardConfig | None = None
    training_params = {}

    if args.board:
        try:
            board_config = load_board(args.board)
            kingdom_cards = board_config.kingdom_cards
            print(f"Using board {args.board}: {', '.join(kingdom_cards)}")
            if board_config.ways:
                print("  Ways: " + ", ".join(board_config.ways))
            if board_config.projects:
                print("  Projects: " + ", ".join(board_config.projects))
            if board_config.events:
                print("  Events: " + ", ".join(board_config.events))
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error loading board: {exc}")
            sys.exit(1)

    if args.kingdom_cards:
        kingdom_cards = args.kingdom_cards
        print(f"Using kingdom cards from command line: {', '.join(kingdom_cards)}")
        board_config = None
    elif args.config and not board_config:
        try:
            kingdom_cards, training_params = load_kingdom_cards_from_yaml(args.config)
            print(f"Using kingdom cards from {args.config}: {', '.join(kingdom_cards)}")
            if training_params:
                print("Loaded training parameters from config file")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error loading config file: {e}")
            sys.exit(1)
    if kingdom_cards is None:
        # Default kingdom cards
        kingdom_cards = [
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
        ]
        print(f"Using default kingdom cards: {', '.join(kingdom_cards)}")

    # Use parameters from command line args, falling back to YAML config, then defaults
    population_size = args.population_size or training_params.get('population_size', 5)
    generations = args.generations or training_params.get('generations', 10)
    mutation_rate = args.mutation_rate or training_params.get('mutation_rate', 0.1)
    games_per_eval = args.games_per_eval or training_params.get('games_per_eval', 10)

    # Create trainer with parameters
    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=population_size,
        generations=generations,
        mutation_rate=mutation_rate,
        games_per_eval=games_per_eval,
        board_config=board_config,
    )

    print("\nTraining parameters:")
    print(f"  Population size: {population_size}")
    print(f"  Generations: {generations}")
    print(f"  Mutation rate: {mutation_rate}")
    print(f"  Games per evaluation: {games_per_eval}")

    # Run training
    best_strategy, metrics = trainer.train()

    print("\nTraining complete!")
    print(f"Final metrics: {metrics}")

    if best_strategy is None:
        print("\nNo viable strategy was found.")
    else:
        print("\nBest strategy card priorities:")
        for rule in best_strategy.gain_priority:
            condition_str = f" (condition: {rule.condition})" if rule.condition else ""
            print(f"  {rule.card_name}{condition_str}")

        # Automatically save the strategy as a Python class
        strategies_dir = Path("generated_strategies")
        strategies_dir.mkdir(exist_ok=True)

        # Create a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_filename = f"strategy_{timestamp}.py"
        strategy_path = strategies_dir / strategy_filename
        class_name = f"Strategy{timestamp}"

        # Save the strategy
        try:
            save_strategy_as_python(best_strategy, strategy_path, class_name)
            print(f"\n✅ Strategy automatically saved to: {strategy_path}")
            print(f"Class name: {class_name}")
            print(f"Win rate vs BigMoney: {metrics.get('win_rate', 'Unknown'):.1f}%")
        except Exception as e:
            print(f"\n❌ Error saving strategy: {e}")


if __name__ == "__main__":
    main()
