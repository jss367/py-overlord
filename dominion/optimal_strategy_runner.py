import copy
import random
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from dominion.simulation.strategy_battle import StrategyBattle


class ImprovedYamlGeneticTrainer:
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
        self.temp_dir = Path("temp_strategies")
        self.strategies_dir = Path("strategies")

        # Create necessary directories
        self.temp_dir.mkdir(exist_ok=True)
        self.strategies_dir.mkdir(exist_ok=True)

        # Initialize battle system and ensure strategies directory exists
        self.battle_system = StrategyBattle(kingdom_cards, log_folder)

    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def save_temp_strategy(self, strategy: dict[str, Any], identifier: str) -> Path:
        """Save a strategy to a temporary file and return the path"""
        filepath = self.temp_dir / f"{identifier}.yaml"
        with open(filepath, "w") as f:
            yaml.dump(strategy, f)
        return filepath

    def evaluate_strategy(self, strategy: dict[str, Any], identifier: str) -> float:
        """Evaluate a strategy by playing games against base strategies"""
        # Set the strategy name for tracking
        strategy["strategy"]["metadata"]["name"] = identifier

        # Save strategy to strategies directory
        strategy_path = self.strategies_dir / f"{identifier}.yaml"
        try:
            with open(strategy_path, "w") as f:
                yaml.dump(strategy, f)

            # Reload strategies to pick up the new one
            self.battle_system.strategy_loader.load_directory(self.strategies_dir)

            # Battle against basic strategies
            base_strategies = ["BigMoney"]
            total_win_rate = 0.0
            games_played = 0

            for opponent in base_strategies:
                try:
                    results = self.battle_system.run_battle(identifier, opponent, num_games=self.games_per_eval)
                    total_win_rate += results["strategy1_win_rate"]
                    games_played += 1
                except Exception as e:
                    print(f"Error in battle against {opponent}: {e}")
                    continue

            # Clean up the temporary strategy file
            strategy_path.unlink()

            return total_win_rate / max(1, games_played) if games_played > 0 else 0.0

        except Exception as e:
            print(f"Error evaluating strategy {identifier}: {e}")
            if strategy_path.exists():
                strategy_path.unlink()
            return 0.0

    def create_random_strategy(self, strategy_id: int) -> dict[str, Any]:
        """Create a random strategy with proper structure"""
        strategy = {
            "strategy": {
                "metadata": {
                    "name": f"Evolved-Strategy-{strategy_id}",
                    "description": "Genetically evolved strategy",
                    "version": "1.0",
                    "creation_date": datetime.now().strftime("%Y-%m-%d"),
                },
                "gainPriority": [],
                "play_priorities": {"default": {}},
                "weights": {
                    "action": round(random.uniform(0.5, 0.9), 2),
                    "treasure": round(random.uniform(0.4, 0.8), 2),
                    "victory": round(random.uniform(0.2, 0.4), 2),
                    "engine": round(random.uniform(0.6, 1.0), 2),
                },
            }
        }

        # Add gain priorities
        all_cards = self.kingdom_cards + [
            "Copper",
            "Silver",
            "Gold",
            "Estate",
            "Duchy",
            "Province",
        ]
        for card in all_cards:
            priority = {"card": card, "priority": round(random.random(), 2)}
            if random.random() < 0.3:
                if card in ["Silver", "Gold", "Province"]:
                    priority["condition"] = f"my.coins >= {3 if card == 'Silver' else 6 if card == 'Gold' else 8}"
                elif card in self.kingdom_cards:
                    priority["condition"] = f"state.turn_number() <= {random.randint(5, 15)}"

            strategy["strategy"]["gainPriority"].append(priority)

        # Add play priorities
        for card in all_cards:
            strategy["strategy"]["play_priorities"]["default"][card] = round(random.random(), 2)

        return strategy

    def train(self) -> tuple[Optional[dict[str, Any]], dict[str, float]]:
        """Run the genetic algorithm training process"""
        try:
            print("Initializing population...")
            population = [self.create_random_strategy(i) for i in range(self.population_size)]

            best_strategy = None
            best_fitness = 0.0

            for gen in range(self.generations):
                print(f"\nGeneration {gen + 1}/{self.generations}")

                # Evaluate population
                fitness_scores = []
                for i, strategy in enumerate(population):
                    fitness = self.evaluate_strategy(strategy, f"gen{gen}-strat{i}")
                    fitness_scores.append(fitness)

                    if fitness > best_fitness:
                        best_fitness = fitness
                        best_strategy = strategy.copy()
                        print(f"New best fitness: {best_fitness:.2f}")

                # Create next generation
                population = self.create_next_generation(population, fitness_scores)

            # Save best strategy
            if best_strategy:
                best_path = self.strategies_dir / "optimal_strategy.yaml"
                with open(best_path, "w") as f:
                    yaml.dump(best_strategy, f)

            metrics = {
                "win_rate": best_fitness,
                "generations": self.generations,
                "final_generation": self.generations,
            }

            return best_strategy, metrics

        except Exception as e:
            print(f"Error during training: {e}")
            return None, {"error": str(e)}
        finally:
            self.cleanup()

    def create_next_generation(
        self, population: list[dict[str, Any]], fitness_scores: list[float]
    ) -> list[dict[str, Any]]:
        """Create the next generation through selection, crossover, and mutation"""
        new_population = []

        # Keep best strategy (elitism)
        best_idx = fitness_scores.index(max(fitness_scores))
        new_population.append(population[best_idx])

        # Create rest through crossover and mutation
        while len(new_population) < self.population_size:
            parent1 = self._tournament_select(population, fitness_scores)
            parent2 = self._tournament_select(population, fitness_scores)

            child = self._crossover(parent1, parent2)
            child = self._mutate(child)

            new_population.append(child)

        return new_population

    def _tournament_select(self, population: list[dict[str, Any]], fitness_scores: list[float]) -> dict[str, Any]:
        """Select a strategy using tournament selection"""
        tournament_size = min(3, len(population))
        tournament_indices = random.sample(range(len(population)), tournament_size)
        winner_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
        return copy.deepcopy(population[winner_idx])

    def _crossover(self, parent1: dict[str, Any], parent2: dict[str, Any]) -> dict[str, Any]:
        """Create a new strategy by combining two parent strategies"""
        child = copy.deepcopy(parent1)
        child_data = child["strategy"]
        parent2_data = parent2["strategy"]

        # Crossover gain priorities
        for i, priority in enumerate(child_data["gainPriority"]):
            if random.random() < 0.5 and i < len(parent2_data["gainPriority"]):
                priority["priority"] = parent2_data["gainPriority"][i]["priority"]
                if "condition" in parent2_data["gainPriority"][i]:
                    priority["condition"] = parent2_data["gainPriority"][i]["condition"]

        # Crossover play priorities
        for card in child_data["play_priorities"]["default"]:
            if random.random() < 0.5 and card in parent2_data["play_priorities"]["default"]:
                child_data["play_priorities"]["default"][card] = parent2_data["play_priorities"]["default"][card]

        # Crossover weights
        for weight_type in child_data["weights"]:
            if random.random() < 0.5:
                child_data["weights"][weight_type] = parent2_data["weights"][weight_type]

        return child

    def _mutate(self, strategy: dict[str, Any]) -> dict[str, Any]:
        """Mutate a strategy"""
        strategy_data = strategy["strategy"]

        # Mutate gain priorities
        for priority in strategy_data["gainPriority"]:
            if random.random() < self.mutation_rate:
                priority["priority"] = round(
                    max(0, min(1, priority["priority"] + (random.random() - 0.5) * 0.4)),
                    2,
                )

        # Mutate play priorities
        for card in strategy_data["play_priorities"]["default"]:
            if random.random() < self.mutation_rate:
                strategy_data["play_priorities"]["default"][card] = round(
                    max(
                        0,
                        min(
                            1,
                            strategy_data["play_priorities"]["default"][card] + (random.random() - 0.5) * 0.4,
                        ),
                    ),
                    2,
                )

        # Mutate weights
        for weight_type in strategy_data["weights"]:
            if random.random() < self.mutation_rate:
                strategy_data["weights"][weight_type] = round(
                    max(
                        0.1,
                        min(
                            1,
                            strategy_data["weights"][weight_type] + (random.random() - 0.5) * 0.4,
                        ),
                    ),
                    2,
                )

        return strategy


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

    trainer = ImprovedYamlGeneticTrainer(
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
