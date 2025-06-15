from datetime import datetime
from pathlib import Path

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


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
    # Define kingdom cards to use
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

    # Create trainer with parameters
    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=5,
        generations=10,
        mutation_rate=0.1,
        games_per_eval=10,
    )

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
            print(f"{rule.card_name}{condition_str}")

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
