from pathlib import Path
import yaml
import random
import copy
from typing import List, Dict, Any
from datetime import datetime
from dominion.simulation.strategy_battle import StrategyBattle
import os


class YamlGeneticTrainer:
    def __init__(
        self,
        kingdom_cards: List[str],
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

        # Create directories if they don't exist
        strategies_dir = Path("strategies")
        strategies_dir.mkdir(exist_ok=True)

        self.battle_system = StrategyBattle(kingdom_cards, log_folder)

    def create_random_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """Create a random strategy in YAML format"""
        # Create gain priority list with conditions
        gain_priority = []
        for card in self.kingdom_cards + [
            "Copper",
            "Silver",
            "Gold",
            "Estate",
            "Duchy",
            "Province",
        ]:
            priority = {"card": card, "priority": round(random.random(), 2)}

            # Add conditions for certain cards
            if card == "Province":
                priority["condition"] = "my.coins >= 8"
            elif card == "Gold":
                priority["condition"] = "my.coins >= 6"
            elif card == "Silver":
                priority["condition"] = "my.coins >= 3"
            elif random.random() < 0.3:  # 30% chance for random condition
                priority["condition"] = self._generate_random_condition()

            gain_priority.append(priority)

        # Create strategy structure
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
                "gainPriority": gain_priority,
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
                    "victory": {
                        "default": round(random.uniform(0.2, 0.4), 2),
                        "endgame": round(random.uniform(0.7, 0.9), 2),
                    },
                    "engine": round(random.uniform(0.6, 1.0), 2),
                },
            }
        }
        return strategy

    def crossover(
        self, parent1: Dict[str, Any], parent2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new strategy by combining two parents"""
        # Ensure we're working with valid strategy structures
        if "strategy" not in parent1 or "strategy" not in parent2:
            raise ValueError("Invalid strategy format - missing 'strategy' key")

        child = copy.deepcopy(parent1)
        parent1_strategy = parent1["strategy"]
        parent2_strategy = parent2["strategy"]

        # Crossover gain priorities
        if "gainPriority" in parent1_strategy and "gainPriority" in parent2_strategy:
            crossover_point = random.randint(0, len(parent1_strategy["gainPriority"]))
            child["strategy"]["gainPriority"] = (
                parent1_strategy["gainPriority"][:crossover_point]
                + parent2_strategy["gainPriority"][crossover_point:]
            )

        # Crossover play priorities
        if (
            "play_priorities" in parent1_strategy
            and "play_priorities" in parent2_strategy
        ):

            child["strategy"]["play_priorities"] = {"default": {}}
            default1 = parent1_strategy["play_priorities"].get("default", {})
            default2 = parent2_strategy["play_priorities"].get("default", {})

            all_cards = set(list(default1.keys()) + list(default2.keys()))
            for card in all_cards:
                if random.random() < 0.5:
                    value = default1.get(card, 0.5)  # Default to 0.5 if missing
                else:
                    value = default2.get(card, 0.5)
                child["strategy"]["play_priorities"]["default"][card] = value

        # Crossover weights
        if "weights" in parent1_strategy and "weights" in parent2_strategy:
            child["strategy"]["weights"] = {}
            # Handle simple weights
            for weight_type in ["action", "treasure", "engine"]:
                if random.random() < 0.5:
                    child["strategy"]["weights"][weight_type] = parent1_strategy[
                        "weights"
                    ][weight_type]
                else:
                    child["strategy"]["weights"][weight_type] = parent2_strategy[
                        "weights"
                    ][weight_type]

            # Handle victory weight specially since it can be nested
            if random.random() < 0.5:
                child["strategy"]["weights"]["victory"] = copy.deepcopy(
                    parent1_strategy["weights"]["victory"]
                )
            else:
                child["strategy"]["weights"]["victory"] = copy.deepcopy(
                    parent2_strategy["weights"]["victory"]
                )

        return child

    def mutate_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate a strategy while maintaining YAML structure"""
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
                                1,
                                priority.get("priority", 0.5)
                                + (random.random() - 0.5) * 0.4,
                            ),
                        ),
                        2,
                    )
                    if random.random() < self.mutation_rate:
                        if "condition" in priority:
                            if random.random() < 0.3:  # 30% chance to remove condition
                                del priority["condition"]
                            else:  # 70% chance to change condition
                                priority["condition"] = (
                                    self._generate_random_condition()
                                )
                        elif random.random() < 0.3:  # 30% chance to add condition
                            priority["condition"] = self._generate_random_condition()

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

        # Mutate weights
        if "weights" in strategy_data:
            for weight_type in ["action", "treasure", "victory", "engine"]:
                if random.random() < self.mutation_rate:
                    strategy_data["weights"][weight_type] = round(
                        max(
                            0.1,
                            min(
                                1,
                                strategy_data["weights"][weight_type]
                                + (random.random() - 0.5) * 0.4,
                            ),
                        ),
                        2,
                    )

        return new_strategy

    def _generate_random_condition(self) -> str:
        """Generate a random condition for card priority"""
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
