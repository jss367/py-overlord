from pathlib import Path
import importlib.util

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def train_optimal_strategy():
    """Main function to train an optimal strategy, building on existing optimal strategy if it exists"""
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

    # Set up paths
    strategies_dir = Path("strategies")
    strategies_dir.mkdir(exist_ok=True)
    optimal_strategy_path = strategies_dir / "optimal_strategy.py"

    # Load existing optimal strategy if it exists
    existing_optimal = None
    if optimal_strategy_path.exists():
        try:
            spec = importlib.util.spec_from_file_location("optimal_strategy", optimal_strategy_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "create_optimal_strategy"):
                    existing_optimal = module.create_optimal_strategy()
                    print("\nLoaded existing optimal strategy")
        except Exception as e:
            print(f"\nError loading existing optimal strategy: {e}")

    # Create trainer with existing optimal strategy in initial population
    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=5,
        generations=4,
        mutation_rate=0.1,
        games_per_eval=4,
        log_folder="optimal_strategy_logs",
    )

    # If we have an existing optimal strategy, inject it
    if existing_optimal:
        trainer.inject_strategy(existing_optimal)

    print("\nStarting training process...")
    new_strategy, metrics = trainer.train()

    # ``GeneticTrainer.train`` returns a BaseStrategy which already extends ``EnhancedStrategy``
    # so no conversion is necessary here.

    if existing_optimal:
        # Battle new strategy against existing optimal
        battle = StrategyBattle(kingdom_cards)
        battle_name = f"gen{trainer.current_generation}-best"
        results = battle.run_battle(battle_name, "optimal_strategy", num_games=20)

        if results["strategy1_win_rate"] > 55:
            print(f"\nNew strategy superior! Win rate vs old: {results['strategy1_win_rate']:.1f}%")
            save_strategy = new_strategy
        else:
            print(f"\nNew strategy not superior. Win rate vs old: {results['strategy1_win_rate']:.1f}%")
            save_strategy = existing_optimal
    else:
        save_strategy = new_strategy

    def save_strategy_as_python(strategy: EnhancedStrategy, path: Path) -> None:
        """Serialize an :class:`EnhancedStrategy` as a Python module."""

        def format_list(name: str, rules: list[PriorityRule]) -> list[str]:
            lines = [f"        self.{name} = ["]
            for rule in rules:
                if rule.condition:
                    lines.append(
                        f"            PriorityRule({rule.card_name!r}, {rule.condition!r}),"
                    )
                else:
                    lines.append(f"            PriorityRule({rule.card_name!r}),")
            lines.append("        ]")
            return lines

        lines = [
            "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule",
            "",
            "",
            "class OptimalStrategy(EnhancedStrategy):",
            "    def __init__(self) -> None:",
            "        super().__init__()",
            f"        self.name = {strategy.name!r}",
        ]

        if strategy.gain_priority:
            lines.extend(format_list("gain_priority", strategy.gain_priority))
        if strategy.action_priority:
            lines.extend(format_list("action_priority", strategy.action_priority))
        if strategy.treasure_priority:
            lines.extend(format_list("treasure_priority", strategy.treasure_priority))
        if strategy.trash_priority:
            lines.extend(format_list("trash_priority", strategy.trash_priority))
        if getattr(strategy, "discard_priority", None):
            lines.extend(format_list("discard_priority", strategy.discard_priority))

        lines.append("")
        lines.append("def create_optimal_strategy() -> EnhancedStrategy:")
        lines.append("    return OptimalStrategy()")

        path.write_text("\n".join(lines), encoding="utf-8")

    # Save strategy to Python file
    save_strategy_as_python(save_strategy, optimal_strategy_path)

    print(f"\nFinal strategy win rate vs BigMoney: {metrics['win_rate']:.1f}%")
    print("\nOptimal Strategy gain priorities:")
    for rule in save_strategy.gain_priority:
        print(f"  - {rule.card_name}: {rule.condition}")

    return save_strategy, metrics


if __name__ == "__main__":
    train_optimal_strategy()
