from dominion.simulation.genetic_trainer import GeneticTrainer

def main():
    # Define kingdom cards to use
    kingdom_cards = [
        "Village", "Smithy", "Market", "Festival",
        "Laboratory", "Mine", "Witch", "Moat",
        "Workshop", "Chapel"
    ]

    # Create trainer with parameters
    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=5,
        generations=10,
        mutation_rate=0.1,
        games_per_eval=10
    )

    # Run training
    best_strategy, metrics = trainer.train()

    print("\nTraining complete!")
    print(f"Final metrics: {metrics}")
    print("\nBest strategy card priorities:")
    for card, priority in best_strategy.gain_priorities.items():
        print(f"{card}: {priority:.3f}")

if __name__ == "__main__":
    main()
