from pathlib import Path

import yaml

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.strategy_loader import StrategyLoader


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

    # Set up paths and loader
    strategies_dir = Path("strategies")
    strategies_dir.mkdir(exist_ok=True)

    loader = StrategyLoader()
    loader.load_directory(strategies_dir)

    # Try to get existing optimal strategy
    existing_optimal = loader.get_strategy("optimal_strategy")
    if existing_optimal:
        print("\nLoaded existing optimal strategy")
    else:
        print("\nNo existing optimal strategy found")

    # Create trainer with existing optimal strategy in initial population
    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=5,
        generations=4,
        mutation_rate=0.1,
        games_per_eval=4,
        log_folder="optimal_strategy_logs",
    )

    # If we have an existing optimal strategy, inject it into the initial population
    if existing_optimal:
        trainer.inject_strategy(existing_optimal)

    print("\nStarting training process...")
    new_strategy, metrics = trainer.train()

    if existing_optimal:
        # Battle new strategy against existing optimal
        battle = StrategyBattle(kingdom_cards)
        results = battle.run_battle(
            new_strategy["strategy"]["metadata"]["name"],
            "optimal_strategy",  # Use the strategy name instead of the data
            num_games=20,
        )

        # Only save if new strategy is better
        if results["strategy1_win_rate"] > 55:  # Requires >55% win rate to replace
            print(f"\nNew strategy superior! Win rate vs old: {results['strategy1_win_rate']:.1f}%")
            save_strategy = new_strategy
        else:
            print(f"\nNew strategy not superior. Win rate vs old: {results['strategy1_win_rate']:.1f}%")
            # Get the YAML representation of the existing strategy
            save_strategy = loader.strategies["optimal_strategy"].to_yaml()
    else:
        save_strategy = new_strategy

    # Save the best strategy
    optimal_strategy_path = strategies_dir / "optimal_strategy.yaml"
    with open(optimal_strategy_path, 'w') as f:
        yaml.dump(save_strategy, f)

    print(f"\nFinal strategy win rate vs BigMoney: {metrics['win_rate']:.1f}%")
    print("\nOptimal Strategy priorities:")
    if save_strategy:
        print(yaml.dump(save_strategy["strategy"]["gainPriority"], indent=2))
    else:
        print("No valid strategy found")

    return save_strategy, metrics


if __name__ == "__main__":
    train_optimal_strategy()
