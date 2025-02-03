import copy
import random
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from dominion.simulation.strategy_battle import StrategyBattle


class GeneticTrainer:
    """Trains Dominion strategies using a genetic algorithm."""

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
        self.current_generation = 0

        # Create necessary directories
        self.temp_dir.mkdir(exist_ok=True)
        self.strategies_dir.mkdir(exist_ok=True)

        # Initialize battle system
        self.battle_system = StrategyBattle(kingdom_cards, log_folder)

    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_random_strategy(self, strategy_id: int) -> dict[str, Any]:
        """Create a random strategy with proper structure"""
        strategy = {
            "strategy": {
                "metadata": {
                    "name": f"gen{self.current_generation}-strat{strategy_id}",
                    "description": "Genetically evolved strategy",
                    "version": "1.0",
                },
                "actionPriority": [],
                "gainPriority": [],
            }
        }

        # Add gain priorities for all cards
        for card in self.kingdom_cards + ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province"]:
            priority = {"card": card, "priority": round(random.random(), 2)}
            if random.random() < 0.3:
                if card in ["Silver", "Gold", "Province"]:
                    priority["condition"] = f"my.coins >= {3 if card == 'Silver' else 6 if card == 'Gold' else 8}"
                elif card in self.kingdom_cards:
                    priority["condition"] = f"state.turn_number() <= {random.randint(5, 15)}"
            strategy["strategy"]["gainPriority"].append(priority)

        # Add action priorities
        for card in self.kingdom_cards:
            priority = {"card": card, "priority": round(random.random(), 2)}
            # Maybe add conditions for certain cards
            if random.random() < 0.3:
                if card in ["Village", "Festival"]:
                    priority["condition"] = "my.actions < 2"
                elif card in ["Smithy", "Laboratory"]:
                    priority["condition"] = "my.actions >= 1"

            strategy["strategy"]["actionPriority"].append(priority)

        return strategy

    def evaluate_strategy(self, strategy: dict[str, Any], identifier: str) -> float:
        """Evaluate a strategy by playing games against base strategies"""
        # Set the strategy name for tracking
        if "metadata" not in strategy["strategy"]:
            strategy["strategy"]["metadata"] = {}
        strategy["strategy"]["metadata"]["name"] = identifier

        # Save strategy to file
        strategy_path = self.strategies_dir / f"{identifier}.yaml"
        try:
            with open(strategy_path, "w") as f:
                yaml.dump(strategy, f)

            # Force reload of strategies
            self.battle_system.strategy_loader.load_directory(self.strategies_dir)

            # Battle against BigMoney
            try:
                results = self.battle_system.run_battle(identifier, "BigMoney", num_games=self.games_per_eval)
                win_rate = results["strategy1_win_rate"]
            except Exception as e:
                print(f"Error in battle against BigMoney: {e}")
                win_rate = 0.0

            # Clean up
            strategy_path.unlink()
            return win_rate

        except Exception as e:
            print(f"Error evaluating strategy {identifier}: {e}")
            if strategy_path.exists():
                strategy_path.unlink()
            return 0.0

    def train(self) -> tuple[Optional[dict[str, Any]], dict[str, float]]:
        """Run the genetic algorithm training process"""
        try:
            print("Initializing population...")
            population = [self.create_random_strategy(i) for i in range(self.population_size)]

            best_strategy = None
            best_fitness = 0.0

            for gen in range(self.generations):
                self.current_generation = gen
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

        # Crossover action priorities
        for i, priority in enumerate(child_data["actionPriority"]):
            if random.random() < 0.5 and i < len(parent2_data["actionPriority"]):
                child_data["actionPriority"][i] = copy.deepcopy(parent2_data["actionPriority"][i])

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
                # Possibly add/remove condition
                if random.random() < 0.3:
                    if "condition" in priority:
                        del priority["condition"]
                    else:
                        card = priority["card"]
                        if card in ["Silver", "Gold", "Province"]:
                            priority["condition"] = (
                                f"my.coins >= {3 if card == 'Silver' else 6 if card == 'Gold' else 8}"
                            )
                        elif card in self.kingdom_cards:
                            priority["condition"] = f"state.turn_number() <= {random.randint(5, 15)}"

        # Mutate action priorities
        if random.random() < self.mutation_rate:
            # Shuffle a portion of the action priorities
            actions = strategy_data["actionPriority"]
            split_point = random.randint(0, len(actions))
            shuffled_portion = actions[split_point:]
            random.shuffle(shuffled_portion)
            strategy_data["actionPriority"] = actions[:split_point] + shuffled_portion

        return strategy
