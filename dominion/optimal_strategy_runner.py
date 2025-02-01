from typing import Dict, Any, List
import yaml
import random
import copy
from datetime import datetime
from dominion.simulation.strategy_battle import StrategyBattle
import os
from pathlib import Path


class YamlGeneticTrainer:
    def __init__(
        self,
        kingdom_cards: list[str],
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
        games_per_eval: int = 10,
        log_folder: str = "training_logs",
    ):
        self.kingdom_cards = kingdom_cards
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.games_per_eval = games_per_eval
        self.log_folder = log_folder
        self.battle_system = StrategyBattle(kingdom_cards, log_folder)

    def mutate_strategy(self, strategy: dict) -> dict:
        """Mutate a strategy while handling nested structures properly."""
        new_strategy = copy.deepcopy(strategy)
        strategy_data = new_strategy["strategy"]

        # Mutate gain priorities
        if "gainPriority" in strategy_data:
            for priority in strategy_data["gainPriority"]:
                if random.random() < self.mutation_rate:
                    priority["priority"] = round(
                        max(
                            0,
                            min(
                                1, priority["priority"] + (random.random() - 0.5) * 0.4
                            ),
                        ),
                        2,
                    )

        # Mutate play priorities
        if (
            "play_priorities" in strategy_data
            and "default" in strategy_data["play_priorities"]
        ):
            for card in strategy_data["play_priorities"]["default"]:
                if random.random() < self.mutation_rate:
                    strategy_data["play_priorities"]["default"][card] = round(
                        max(
                            0,
                            min(
                                1,
                                strategy_data["play_priorities"]["default"][card]
                                + (random.random() - 0.5) * 0.4,
                            ),
                        ),
                        2,
                    )

        # Mutate weights with proper handling of nested victory weight
        if "weights" in strategy_data:
            weights = strategy_data["weights"]
            for weight_type in ["action", "treasure", "engine"]:
                if random.random() < self.mutation_rate:
                    weights[weight_type] = round(
                        max(
                            0.1,
                            min(
                                1, weights[weight_type] + (random.random() - 0.5) * 0.4
                            ),
                        ),
                        2,
                    )

            # Handle victory weight which can be either a float or dict
            if random.random() < self.mutation_rate:
                if isinstance(weights["victory"], dict):
                    for key in ["default", "endgame"]:
                        if key in weights["victory"]:
                            weights["victory"][key] = round(
                                max(
                                    0.1,
                                    min(
                                        1,
                                        weights["victory"][key]
                                        + (random.random() - 0.5) * 0.4,
                                    ),
                                ),
                                2,
                            )
                else:
                    weights["victory"] = round(
                        max(
                            0.1,
                            min(1, weights["victory"] + (random.random() - 0.5) * 0.4),
                        ),
                        2,
                    )

        return new_strategy

    def create_random_strategy(self, strategy_id: int) -> dict:
        """Create a random strategy with proper structure."""
        strategy = {
            "strategy": {
                "metadata": {
                    "name": f"Evolved-Strategy-{strategy_id}",
                    "description": "Genetically evolved strategy",
                    "version": "1.0",
                    "creation_date": datetime.now().strftime("%Y-%m-%d"),
                },
                "author": ["GeneticTrainer"],
                "requires": self.kingdom_cards,
                "gainPriority": [
                    {
                        "card": card,
                        "priority": round(random.random(), 2),
                        "condition": (
                            self._generate_random_condition()
                            if random.random() < 0.3
                            else None
                        ),
                    }
                    for card in (
                        self.kingdom_cards
                        + ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province"]
                    )
                ],
                "play_priorities": {
                    "default": {
                        card: round(random.random(), 2)
                        for card in self.kingdom_cards
                        + ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province"]
                    }
                },
                "weights": {
                    "action": round(random.uniform(0.5, 0.9), 2),
                    "treasure": round(random.uniform(0.4, 0.8), 2),
                    "victory": round(random.uniform(0.2, 0.4), 2),
                    "engine": round(random.uniform(0.6, 1.0), 2),
                },
            }
        }
        return strategy

    def _generate_random_condition(self) -> str:
        """Generate a random condition that will work with the strategy runner."""
        conditions = [
            "my.coins >= {}",
            "my.actions >= {}",
            "state.countInSupply('{}') >= {}",
            "my.countInDeck('{}') < {}",
            "state.turn_number() <= {}",
        ]

        condition = random.choice(conditions)

        if "{}" in condition:
            if "countInSupply" in condition or "countInDeck" in condition:
                card = random.choice(self.kingdom_cards)
                number = random.randint(1, 5)
                return condition.format(card, number)
            else:
                return condition.format(random.randint(1, 8))

        return condition

    def evaluate_strategy(self, strategy: Dict[str, Any]) -> float:
        """Evaluate a strategy by playing games against base strategies"""
        strategy_name = strategy["strategy"]["metadata"]["name"]

        # Save strategy temporarily
        strategy_path = Path("strategies/temp_strategy.yaml")
        with open(strategy_path, "w") as f:
            yaml.dump(strategy, f)

        # Battle against basic strategies
        base_strategies = ["BigMoney"]  # Simplified for testing
        total_win_rate = 0

        for opponent in base_strategies:
            try:
                results = self.battle_system.run_battle(
                    strategy_name, opponent, num_games=self.games_per_eval
                )
                total_win_rate += results["strategy1_win_rate"]
            except Exception as e:
                print(f"Error evaluating strategy: {e}")
                return 0.0

        # Clean up temporary file
        strategy_path.unlink()

        return total_win_rate / len(base_strategies)

    def train(self) -> tuple[Dict[str, Any], Dict[str, float]]:
        """Run the genetic algorithm training process"""
        # Create initial population
        population = [
            self.create_random_strategy(i) for i in range(self.population_size)
        ]

        best_strategy = None
        best_fitness = 0.0

        # Run generations
        for gen in range(self.generations):
            print(f"\nGeneration {gen + 1}/{self.generations}")

            # Evaluate current population
            fitness_scores = []
            for strategy in population:
                fitness = self.evaluate_strategy(strategy)
                fitness_scores.append(fitness)

                if fitness > best_fitness:
                    best_fitness = fitness
                    best_strategy = strategy.copy()

            # Create next generation
            new_population = []

            # Elitism: keep best strategy
            best_idx = fitness_scores.index(max(fitness_scores))
            new_population.append(population[best_idx])

            # Create rest of population through crossover and mutation
            while len(new_population) < self.population_size:
                parent1 = self._tournament_select(population, fitness_scores)
                parent2 = self._tournament_select(population, fitness_scores)

                child = self.crossover(parent1, parent2)
                child = self.mutate_strategy(child)

                new_population.append(child)

            population = new_population
            print(f"Best fitness: {best_fitness:.2f}")

        # Save best strategy
        with open("strategies/optimal_strategy.yaml", "w") as f:
            yaml.dump(best_strategy, f)

        metrics = {
            "win_rate": best_fitness,
            "generations": self.generations,
            "final_generation": self.generations,
        }

        return best_strategy, metrics

    def _tournament_select(
        self, population: List[Dict[str, Any]], fitness_scores: List[float]
    ) -> Dict[str, Any]:
        """Select a strategy using tournament selection"""
        tournament_size = 3
        tournament_indices = random.sample(range(len(population)), tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[
            tournament_fitness.index(max(tournament_fitness))
        ]
        return population[winner_idx]

    def crossover(
        self, parent1: Dict[str, Any], parent2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new strategy by combining two parent strategies with proper YAML structure."""
        # Create a new strategy with metadata from parent1
        child = copy.deepcopy(parent1)
        strategy_data = child["strategy"]
        parent2_data = parent2["strategy"]

        # Crossover gain priorities
        if "gainPriority" in strategy_data and "gainPriority" in parent2_data:
            for i, priority in enumerate(strategy_data["gainPriority"]):
                if i < len(parent2_data["gainPriority"]):
                    weight = random.random()
                    # Crossover priority values while keeping card and condition
                    priority["priority"] = round(
                        priority["priority"] * weight
                        + parent2_data["gainPriority"][i]["priority"] * (1 - weight),
                        2,
                    )

        # Crossover play priorities
        if (
            "play_priorities" in strategy_data
            and "play_priorities" in parent2_data
            and "default" in strategy_data["play_priorities"]
            and "default" in parent2_data["play_priorities"]
        ):

            p1_priorities = strategy_data["play_priorities"]["default"]
            p2_priorities = parent2_data["play_priorities"]["default"]

            for card in p1_priorities:
                if card in p2_priorities:
                    weight = random.random()
                    p1_priorities[card] = round(
                        p1_priorities[card] * weight
                        + p2_priorities[card] * (1 - weight),
                        2,
                    )

        # Crossover weights
        if "weights" in strategy_data and "weights" in parent2_data:
            p1_weights = strategy_data["weights"]
            p2_weights = parent2_data["weights"]

            # Handle basic weights
            for weight_type in ["action", "treasure", "engine"]:
                if weight_type in p1_weights and weight_type in p2_weights:
                    weight = random.random()
                    p1_weights[weight_type] = round(
                        p1_weights[weight_type] * weight
                        + p2_weights[weight_type] * (1 - weight),
                        2,
                    )

            # Handle victory weight which could be either float or dict
            if "victory" in p1_weights and "victory" in p2_weights:
                if isinstance(p1_weights["victory"], dict) and isinstance(
                    p2_weights["victory"], dict
                ):
                    # Both are dicts, crossover each component
                    for key in ["default", "endgame"]:
                        if (
                            key in p1_weights["victory"]
                            and key in p2_weights["victory"]
                        ):
                            weight = random.random()
                            p1_weights["victory"][key] = round(
                                p1_weights["victory"][key] * weight
                                + p2_weights["victory"][key] * (1 - weight),
                                2,
                            )
                else:
                    # At least one is a float, treat both as floats
                    p1_val = (
                        p1_weights["victory"]["default"]
                        if isinstance(p1_weights["victory"], dict)
                        else p1_weights["victory"]
                    )
                    p2_val = (
                        p2_weights["victory"]["default"]
                        if isinstance(p2_weights["victory"], dict)
                        else p2_weights["victory"]
                    )
                    weight = random.random()
                    p1_weights["victory"] = round(
                        p1_val * weight + p2_val * (1 - weight), 2
                    )

        return child


def train_optimal_strategy():
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

    trainer = YamlGeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=5,
        generations=4,
        mutation_rate=0.1,
        games_per_eval=4,
        log_folder="optimal_strategy_logs",
    )

    print("Starting training process...")
    best_strategy, metrics = trainer.train()

    print("\nTraining completed!")
    print(f"\nBest strategy win rate: {metrics['win_rate']:.2f}%")
    print("\nOptimal Strategy:")
    print(yaml.dump(best_strategy, indent=2))

    return best_strategy, metrics


if __name__ == "__main__":
    train_optimal_strategy()
