import yaml

from dominion.simulation.genetic_trainer import GeneticTrainer


def train_optimal_strategy():
    """Main function to train an optimal strategy"""
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

    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=5,
        generations=4,
        mutation_rate=0.1,
        games_per_eval=4,
        log_folder="optimal_strategy_logs",
    )

    print("\nStarting training process...")
    best_strategy, metrics = trainer.train()

    print("\nTraining completed!")
    if best_strategy:
        print(f"\nBest strategy win rate: {metrics['win_rate']:.2f}%")
        print("\nOptimal Strategy:")
        print(yaml.dump(best_strategy, indent=2))
    else:
        print("\nTraining failed:", metrics.get("error", "Unknown error"))

    return best_strategy, metrics


if __name__ == "__main__":
    train_optimal_strategy()
