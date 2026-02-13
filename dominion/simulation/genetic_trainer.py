import logging
import random
from copy import deepcopy
from typing import Optional, Tuple

import coloredlogs

from dominion.boards.loader import BoardConfig
from dominion.simulation.game_logger import GameLogger
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy

log = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=log)


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
        board_config: Optional[BoardConfig] = None,
    ):
        if kingdom_cards is None:
            if board_config is None:
                kingdom_cards = []
            else:
                kingdom_cards = board_config.kingdom_cards

        self.kingdom_cards = kingdom_cards
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.games_per_eval = games_per_eval
        self.board_config = board_config
        self.battle_system = StrategyBattle(kingdom_cards, log_folder, board_config=board_config)
        if not self.kingdom_cards:
            raise ValueError("kingdom_cards cannot be empty")
        self.current_generation = 0
        self.logger = GameLogger(log_folder)
        self._strategy_to_inject = None
        self._baseline_strategy = None

    @staticmethod
    def _random_condition() -> "Callable | None":
        """Return a random callable condition from a diverse vocabulary."""
        kind = random.choice([
            "provinces_left", "turn_number", "resources", "has_cards", "none",
        ])
        if kind == "provinces_left":
            op = random.choice(["<=", ">", ">=", "<"])
            amount = random.randint(2, 8)
            return PriorityRule.provinces_left(op, amount)
        if kind == "turn_number":
            op = random.choice(["<=", ">=", "<", ">"])
            amount = random.randint(3, 18)
            return PriorityRule.turn_number(op, amount)
        if kind == "resources":
            res = random.choice(["coins", "actions", "buys"])
            op = random.choice([">=", "<", "<=", ">"])
            amount = random.randint(1, 8)
            return PriorityRule.resources(res, op, amount)
        if kind == "has_cards":
            cards = random.sample(
                ["Silver", "Gold", "Copper", "Province", "Duchy", "Estate"],
                k=random.randint(1, 3),
            )
            amount = random.randint(0, 4)
            return PriorityRule.has_cards(cards, amount)
        return None

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

        # Generate gain priorities (random subset in random order)
        gain_cards = list(all_cards)
        random.shuffle(gain_cards)
        strategy.gain_priority = []
        for card in gain_cards:
            condition = None
            if random.random() < 0.3:
                if card in ["Silver", "Gold", "Province"]:
                    cost = {"Silver": 3, "Gold": 6, "Province": 8}[card]
                    condition = PriorityRule.resources("coins", ">=", cost)
                elif card in self.kingdom_cards:
                    condition = PriorityRule.turn_number("<=", random.randint(5, 15))
                else:
                    condition = self._random_condition()
            strategy.gain_priority.append(PriorityRule(card, condition))

        # Generate action priorities
        strategy.action_priority = []
        action_cards = list(self.kingdom_cards)
        random.shuffle(action_cards)
        for card in action_cards:
            if random.random() < 0.7:  # 70% chance to include each action
                condition = None
                if random.random() < 0.3:
                    if card in ["Village", "Festival"]:
                        condition = PriorityRule.resources("actions", "<", 2)
                    elif card in ["Smithy", "Laboratory"]:
                        condition = PriorityRule.resources("actions", ">=", 1)
                    else:
                        condition = self._random_condition()
                strategy.action_priority.append(PriorityRule(card, condition))

        # Generate treasure priorities — include kingdom treasures
        kingdom_treasures = []
        for card_name in self.kingdom_cards:
            try:
                from dominion.cards.registry import get_card
                card = get_card(card_name)
                if card.is_treasure:
                    kingdom_treasures.append(card_name)
            except ValueError:
                pass
        treasure_list = kingdom_treasures + ["Gold", "Silver", "Copper"]
        random.shuffle(treasure_list)
        strategy.treasure_priority = [PriorityRule(t) for t in treasure_list]

        # Generate trash priorities
        strategy.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]

        return self._normalize(strategy)

    def set_baseline_strategy(self, strategy: BaseStrategy):
        """Set a custom baseline strategy to evaluate against instead of Big Money."""
        self._baseline_strategy = strategy

    def evaluate_strategy(self, strategy: BaseStrategy) -> float:
        """Evaluate a strategy by playing a series of games against the baseline."""
        try:
            if self._baseline_strategy is not None:
                opponent = self._baseline_strategy
            else:
                opponent = self.battle_system.strategy_loader.get_strategy("Big Money")
                if not opponent:
                    raise ValueError("Big Money strategy not found")

            kingdom_card_names = self.battle_system._determine_kingdom_cards(strategy, opponent)

            from dominion.ai.genetic_ai import GeneticAI

            wins = 0
            for game_num in range(self.games_per_eval):
                ai1 = GeneticAI(strategy)
                ai2 = GeneticAI(opponent)

                if game_num % 2 == 0:
                    winner, _scores, _log, _turns = self.battle_system.run_game(ai1, ai2, kingdom_card_names)
                    if winner == ai1:
                        wins += 1
                else:
                    winner, _scores, _log, _turns = self.battle_system.run_game(ai2, ai1, kingdom_card_names)
                    if winner == ai1:
                        wins += 1
            return wins / self.games_per_eval * 100
        except Exception as e:
            log.exception("Error evaluating strategy %s. Got error: %s", strategy.name, e)
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
        # --- Mutate gain priorities ---
        # Condition mutations
        for priority in strategy.gain_priority:
            if random.random() < self.mutation_rate:
                if random.random() < 0.3:
                    if priority.condition:
                        priority.condition = None
                    else:
                        if priority.card_name in ["Silver", "Gold", "Province"]:
                            cost = {"Silver": 3, "Gold": 6, "Province": 8}[priority.card_name]
                            priority.condition = PriorityRule.resources("coins", ">=", cost)
                        elif priority.card_name in self.kingdom_cards:
                            priority.condition = PriorityRule.turn_number("<=", random.randint(5, 15))
                        else:
                            priority.condition = self._random_condition()

        # Reorder: swap two adjacent gain rules
        if random.random() < self.mutation_rate and len(strategy.gain_priority) >= 2:
            i = random.randint(0, len(strategy.gain_priority) - 2)
            strategy.gain_priority[i], strategy.gain_priority[i + 1] = (
                strategy.gain_priority[i + 1],
                strategy.gain_priority[i],
            )

        # Occasionally move a random rule to a new position
        if random.random() < self.mutation_rate * 0.5 and len(strategy.gain_priority) >= 2:
            i = random.randint(0, len(strategy.gain_priority) - 1)
            rule = strategy.gain_priority.pop(i)
            j = random.randint(0, len(strategy.gain_priority))
            strategy.gain_priority.insert(j, rule)

        # Add a new kingdom card that's missing from the gain list
        if random.random() < self.mutation_rate * 0.3:
            existing = {r.card_name for r in strategy.gain_priority}
            missing = [c for c in self.kingdom_cards if c not in existing]
            if missing:
                card = random.choice(missing)
                pos = random.randint(0, len(strategy.gain_priority))
                strategy.gain_priority.insert(pos, PriorityRule(card, self._random_condition()))

        # Remove a low-value gain entry (but keep at least 3 rules)
        if random.random() < self.mutation_rate * 0.2 and len(strategy.gain_priority) > 3:
            i = random.randint(0, len(strategy.gain_priority) - 1)
            strategy.gain_priority.pop(i)

        # --- Mutate action priorities ---
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
                                priority.condition = PriorityRule.resources("actions", "<", 2)
                            elif priority.card_name in ["Smithy", "Laboratory"]:
                                priority.condition = PriorityRule.resources("actions", ">=", 1)
                            else:
                                priority.condition = self._random_condition()

        # Add/remove action cards
        if random.random() < self.mutation_rate * 0.3:
            existing = {r.card_name for r in strategy.action_priority}
            missing = [c for c in self.kingdom_cards if c not in existing]
            if missing:
                card = random.choice(missing)
                pos = random.randint(0, len(strategy.action_priority))
                strategy.action_priority.insert(pos, PriorityRule(card, self._random_condition()))

        if random.random() < self.mutation_rate * 0.2 and len(strategy.action_priority) > 1:
            i = random.randint(0, len(strategy.action_priority) - 1)
            strategy.action_priority.pop(i)

        # --- Mutate treasure priorities ---
        if random.random() < self.mutation_rate and len(strategy.treasure_priority) >= 2:
            i = random.randint(0, len(strategy.treasure_priority) - 2)
            strategy.treasure_priority[i], strategy.treasure_priority[i + 1] = (
                strategy.treasure_priority[i + 1],
                strategy.treasure_priority[i],
            )

        # Add missing kingdom treasures to treasure priority
        if random.random() < self.mutation_rate * 0.3:
            existing_treasures = {r.card_name for r in strategy.treasure_priority}
            for card_name in self.kingdom_cards:
                if card_name in existing_treasures:
                    continue
                try:
                    from dominion.cards.registry import get_card
                    card = get_card(card_name)
                    if card.is_treasure:
                        pos = random.randint(0, len(strategy.treasure_priority))
                        strategy.treasure_priority.insert(pos, PriorityRule(card_name))
                except ValueError:
                    pass

        # --- Mutate trash priorities ---
        if random.random() < self.mutation_rate:
            if strategy.trash_priority:
                for priority in strategy.trash_priority:
                    if random.random() < 0.3:
                        if priority.card_name == "Estate":
                            priority.condition = PriorityRule.provinces_left(">", random.randint(2, 6))
                        elif priority.card_name == "Copper":
                            min_treasures = random.randint(2, 4)
                            priority.condition = PriorityRule.has_cards(["Silver", "Gold"], min_treasures)

        return strategy

    @staticmethod
    def _normalize_priority_list(rules: list[PriorityRule]) -> list[PriorityRule]:
        """Remove unreachable rules from a priority list.

        Once an unconditional rule for a card is seen, all subsequent rules
        for that card are dead code (the unconditional rule always matches first).
        """
        seen_unconditional: set[str] = set()
        result = []
        for rule in rules:
            if rule.card_name in seen_unconditional:
                continue
            if rule.condition is None:
                seen_unconditional.add(rule.card_name)
            result.append(rule)
        return result

    def _normalize(self, strategy: BaseStrategy) -> BaseStrategy:
        """Normalize all priority lists to remove unreachable rules."""
        strategy.gain_priority = self._normalize_priority_list(strategy.gain_priority)
        strategy.action_priority = self._normalize_priority_list(strategy.action_priority)
        strategy.treasure_priority = self._normalize_priority_list(strategy.treasure_priority)
        strategy.trash_priority = self._normalize_priority_list(strategy.trash_priority)
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
            child = self._normalize(child)
            child.name = f"gen{self.current_generation}-{id(child)}"

            new_population.append(child)

        return new_population

    def train(self) -> Tuple[Optional[BaseStrategy], dict]:
        """Run the genetic algorithm training process"""
        try:
            log.info("Initializing population...")
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
                log.info("Generation %d/%d", gen + 1, self.generations)

                # Evaluate population
                fitness_scores = []
                for i, strategy in enumerate(population):
                    fitness = self.evaluate_strategy(strategy)
                    fitness_scores.append(fitness)

                    if fitness > best_fitness:
                        best_fitness = fitness
                        best_strategy = deepcopy(strategy)
                        log.info("New best fitness: %.2f", best_fitness)

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

        except Exception as exc:
            log.exception("Error during training")
            return None, {"error": str(exc)}

    def inject_strategy(self, strategy: BaseStrategy):
        """Inject an existing strategy into the initial population.
        This should be called before train() is called."""
        self._strategy_to_inject = strategy
