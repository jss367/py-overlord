import random
from copy import deepcopy
from typing import Optional, Tuple

from dominion.simulation.game_logger import GameLogger
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


class GeneticTrainer:
    """Trains Dominion strategies using a genetic algorithm"""

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
        self.battle_system = StrategyBattle(kingdom_cards, log_folder)
        self.current_generation = 0
        self.logger = GameLogger(log_folder)
        self._strategy_to_inject = None

    def create_random_strategy(self) -> BaseStrategy:
        """Create a random strategy"""
        strategy = BaseStrategy()
        strategy.name = f"gen{self.current_generation}-{id(strategy)}"

        # All possible cards
        all_cards = (
            self.kingdom_cards
            + ["Copper", "Silver", "Gold"]  # Treasures
            + ["Estate", "Duchy", "Province"]  # Victory cards
        )

        # Generate gain priorities
        strategy.gain_priority = []
        for card in all_cards:
            condition = None
            if random.random() < 0.3:
                if card in ["Silver", "Gold", "Province"]:
                    cost = {"Silver": 3, "Gold": 6, "Province": 8}[card]
                    condition = f"my.coins >= {cost}"
                elif card in self.kingdom_cards:
                    condition = f"state.turn_number <= {random.randint(5, 15)}"

            strategy.gain_priority.append(PriorityRule(card, condition))

        # Generate action priorities
        strategy.action_priority = []
        for card in self.kingdom_cards:
            if random.random() < 0.7:  # 70% chance to include each action
                condition = None
                if random.random() < 0.3:
                    if card in ["Village", "Festival"]:
                        condition = "my.actions < 2"
                    elif card in ["Smithy", "Laboratory"]:
                        condition = "my.actions >= 1"
                strategy.action_priority.append(PriorityRule(card, condition))

        # Generate treasure priorities
        strategy.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        # Generate trash priorities
        strategy.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", "state.provinces_left > 4"),
            PriorityRule("Copper", "my.count(Silver) + my.count(Gold) >= 3"),
        ]

        return strategy

    def evaluate_strategy(self, strategy: BaseStrategy) -> float:
        """Evaluate a strategy by playing against BigMoney"""
        try:
            results = self.battle_system.run_battle(
                strategy, self.battle_system.registry.get_strategy("BigMoney"), self.games_per_eval
            )
            return results["strategy1_win_rate"]
        except Exception as e:
            print(f"Error evaluating strategy: {e}")
            return 0.0

    def _crossover(self, parent1: BaseStrategy, parent2: BaseStrategy) -> BaseStrategy:
        """Create a new strategy by combining two parent strategies"""
        child = deepcopy(parent1)

        # Crossover gain priorities
        for i, priority in enumerate(child.gain_priority):
            if random.random() < 0.5 and i < len(parent2.gain_priority):
                child.gain_priority[i] = deepcopy(parent2.gain_priority[i])

        # Crossover action priorities
        if parent2.action_priority:
            split_point = random.randint(0, len(child.action_priority))
            child.action_priority = child.action_priority[:split_point] + deepcopy(
                parent2.action_priority[split_point:]
            )

        # Crossover trash priorities
        if parent2.trash_priority:
            split_point = random.randint(0, len(child.trash_priority))
            child.trash_priority = child.trash_priority[:split_point] + deepcopy(parent2.trash_priority[split_point:])

        # Keep treasure priorities from one parent
        if random.random() < 0.5:
            child.treasure_priority = deepcopy(parent2.treasure_priority)

        return child

    def _mutate(self, strategy: BaseStrategy) -> BaseStrategy:
        """Mutate a strategy"""
        # Mutate gain priorities
        for priority in strategy.gain_priority:
            if random.random() < self.mutation_rate:
                # Possibly add/remove/modify condition
                if random.random() < 0.3:
                    if priority.condition:
                        priority.condition = None
                    else:
                        if priority.card_name in ["Silver", "Gold", "Province"]:
                            cost = {"Silver": 3, "Gold": 6, "Province": 8}[priority.card_name]
                            priority.condition = f"my.coins >= {cost}"
                        elif priority.card_name in self.kingdom_cards:
                            priority.condition = f"state.turn_number <= {random.randint(5, 15)}"

        # Mutate action priorities
        if random.random() < self.mutation_rate:
            if strategy.action_priority:
                # Shuffle a portion of the action priorities
                split_point = random.randint(0, len(strategy.action_priority))
                shuffled = strategy.action_priority[split_point:]
                random.shuffle(shuffled)
                strategy.action_priority = strategy.action_priority[:split_point] + shuffled

                # Possibly modify conditions
                for priority in strategy.action_priority:
                    if random.random() < 0.3:
                        if priority.condition:
                            priority.condition = None
                        else:
                            if priority.card_name in ["Village", "Festival"]:
                                priority.condition = "my.actions < 2"
                            elif priority.card_name in ["Smithy", "Laboratory"]:
                                priority.condition = "my.actions >= 1"

        # Mutate trash priorities
        if random.random() < self.mutation_rate:
            if strategy.trash_priority:
                # Possibly modify conditions
                for priority in strategy.trash_priority:
                    if random.random() < 0.3:
                        if priority.card_name == "Estate":
                            priority.condition = f"state.provinces_left > {random.randint(2, 6)}"
                        elif priority.card_name == "Copper":
                            min_treasures = random.randint(2, 4)
                            priority.condition = f"my.count(Silver) + my.count(Gold) >= {min_treasures}"

        return strategy

    def _tournament_select(self, population: list[BaseStrategy], fitness_scores: list[float]) -> BaseStrategy:
        """Select a strategy using tournament selection"""
        tournament_size = min(3, len(population))
        tournament_indices = random.sample(range(len(population)), tournament_size)
        winner_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
        return deepcopy(population[winner_idx])

    def create_next_generation(self, population: list[BaseStrategy], fitness_scores: list[float]) -> list[BaseStrategy]:
        """Create the next generation through selection, crossover, and mutation"""
        new_population = []

        # Keep best strategy (elitism)
        best_idx = fitness_scores.index(max(fitness_scores))
        new_population.append(deepcopy(population[best_idx]))

        # Create rest through crossover and mutation
        while len(new_population) < self.population_size:
            parent1 = self._tournament_select(population, fitness_scores)
            parent2 = self._tournament_select(population, fitness_scores)

            child = self._crossover(parent1, parent2)
            child = self._mutate(child)
            child.name = f"gen{self.current_generation}-{id(child)}"

            new_population.append(child)

        return new_population

    def train(self) -> Tuple[Optional[BaseStrategy], dict]:
        """Run the genetic algorithm training process"""
        try:
            print("Initializing population...")
            population = [self.create_random_strategy() for _ in range(self.population_size)]

            # Inject strategy if one was provided
            if self._strategy_to_inject is not None:
                replace_idx = random.randint(0, len(population) - 1)
                population[replace_idx] = deepcopy(self._strategy_to_inject)
                self._strategy_to_inject = None

            best_strategy = None
            best_fitness = 0.0

            # Start training progress tracking
            self.logger.start_training(self.generations)

            for gen in range(self.generations):
                self.current_generation = gen
                print(f"\nGeneration {gen + 1}/{self.generations}")

                # Evaluate population
                fitness_scores = []
                for i, strategy in enumerate(population):
                    fitness = self.evaluate_strategy(strategy)
                    fitness_scores.append(fitness)

                    if fitness > best_fitness:
                        best_fitness = fitness
                        best_strategy = deepcopy(strategy)
                        print(f"New best fitness: {best_fitness:.2f}")

                # Calculate generation statistics
                avg_fitness = sum(fitness_scores) / len(fitness_scores)

                # Update progress
                self.logger.update_training(gen, best_fitness, avg_fitness)

                # Create next generation
                population = self.create_next_generation(population, fitness_scores)

            # End training progress tracking
            self.logger.end_training()

            metrics = {
                "win_rate": best_fitness,
                "generations": self.generations,
                "final_generation": self.generations,
            }

            return best_strategy, metrics

        except Exception as e:
            print(f"Error during training: {e}")
            return None, {"error": str(e)}

    def inject_strategy(self, strategy: BaseStrategy):
        """Inject an existing strategy into the initial population.
        This should be called before train() is called."""
        self._strategy_to_inject = strategy
