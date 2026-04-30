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


def _distribute_games(total_budget: int, n_opponents: int) -> list[int]:
    """Distribute ``total_budget`` games across ``n_opponents``, preserving the
    budget exactly when feasible. Each opponent gets ``base`` games and the
    first ``remainder`` opponents get one extra. If the budget is smaller than
    the panel (degenerate case), every opponent still gets at least 1 game so
    no opponent is silently skipped — this overruns the budget but preserves
    the panel semantic."""
    if n_opponents <= 0:
        return []
    if total_budget < n_opponents:
        return [1] * n_opponents
    base, remainder = divmod(total_budget, n_opponents)
    return [base + (1 if i < remainder else 0) for i in range(n_opponents)]


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
        immigrant_fraction: float = 0.15,
        sharing_threshold: float = 0.8,
        simplify_genomes: bool = True,
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
        self.immigrant_fraction = immigrant_fraction
        self.sharing_threshold = sharing_threshold
        self.simplify_genomes = simplify_genomes
        self.battle_system = StrategyBattle(kingdom_cards, log_folder, board_config=board_config)
        if not self.kingdom_cards:
            raise ValueError("kingdom_cards cannot be empty")
        self.current_generation = 0
        self.logger = GameLogger(log_folder)
        self._strategy_to_inject = None
        self._baseline_strategy = None
        self._baseline_panel: list[BaseStrategy] = []
        # List of (opponent_name, win_rate) tuples — list (not dict) so that
        # multiple panel members sharing a name (e.g. two BigMoneySmithy
        # variants) each contribute their rate independently.
        self.last_eval_breakdown: list[tuple[str, float]] = []

        # Cache card type lookups for filtering
        from dominion.cards.registry import get_card
        self._kingdom_action_cards = []
        self._kingdom_treasure_cards = []
        for card_name in self.kingdom_cards:
            try:
                card = get_card(card_name)
                if card.is_action:
                    self._kingdom_action_cards.append(card_name)
                if card.is_treasure:
                    self._kingdom_treasure_cards.append(card_name)
            except ValueError:
                pass

    # Probability that ``_random_condition_with_compound`` wraps a normally
    # sampled inner condition in ``and_(card_in_play(X), inner)``. Tunable.
    _COMPOUND_CONDITION_PROB = 0.15

    def _random_condition_with_compound(self) -> "Callable | None":
        """Return a random callable condition, with ~15% probability returning
        a compound ``and_(card_in_play(X), inner)`` where ``X`` is drawn from
        the kingdom's action cards and ``inner`` is a normally-sampled
        condition.

        If the kingdom has no action cards, falls back to a non-compound
        condition (since ``card_in_play`` with no kingdom action is not
        meaningful).
        """
        if (
            self._kingdom_action_cards
            and random.random() < self._COMPOUND_CONDITION_PROB
        ):
            inner = self._random_condition()
            card = random.choice(self._kingdom_action_cards)
            if inner is None:
                # A degenerate ``and_(card_in_play(X))`` collapses to just the
                # card_in_play check; emit it directly so the _source string
                # stays clean.
                return PriorityRule.card_in_play(card)
            return PriorityRule.and_(PriorityRule.card_in_play(card), inner)
        return self._random_condition()

    def _random_condition(self) -> "Callable | None":
        """Return a random callable condition from a diverse vocabulary.

        card_in_play requires a real kingdom action card name, so this is
        an instance method (not a staticmethod) — it pulls the candidate set
        from self._kingdom_action_cards computed in __init__."""
        choices = [
            "provinces_left", "turn_number", "resources", "has_cards",
            "empty_piles", "deck_size", "action_density", "score_diff",
            "actions_in_play", "max_in_deck",
            "actions_gained_this_turn", "cards_gained_this_turn",
            "none",
        ]
        # card_in_play only makes sense if we have at least one kingdom
        # action card to reference.
        if self._kingdom_action_cards:
            choices.append("card_in_play")
        kind = random.choice(choices)
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
        if kind == "empty_piles":
            op = random.choice([">=", ">", "<="])
            amount = random.randint(1, 4)
            return PriorityRule.empty_piles(op, amount)
        if kind == "deck_size":
            op = random.choice(["<=", ">=", "<", ">"])
            amount = random.randint(8, 35)
            return PriorityRule.deck_size(op, amount)
        if kind == "action_density":
            op = random.choice([">=", "<="])
            percent = random.choice([20, 30, 40, 50, 60])
            return PriorityRule.action_density(op, percent)
        if kind == "score_diff":
            op = random.choice([">=", "<=", ">", "<"])
            amount = random.choice([-12, -6, -3, 0, 3, 6, 12])
            return PriorityRule.score_diff(op, amount)
        if kind == "actions_in_play":
            op = random.choice([">=", "<=", ">", "<"])
            amount = random.randint(0, 4)
            return PriorityRule.actions_in_play(op, amount)
        if kind == "max_in_deck":
            card = random.choice(["Silver", "Gold", "Copper", "Estate", "Curse"])
            amount = random.randint(1, 6)
            return PriorityRule.max_in_deck(card, amount)
        if kind == "actions_gained_this_turn":
            op = random.choice(["<=", ">=", "<", ">"])
            amount = random.randint(1, 4)
            return PriorityRule.actions_gained_this_turn(op, amount)
        if kind == "cards_gained_this_turn":
            op = random.choice(["<=", ">=", "<", ">"])
            amount = random.randint(1, 5)
            return PriorityRule.cards_gained_this_turn(op, amount)
        if kind == "card_in_play":
            card = random.choice(self._kingdom_action_cards)
            return PriorityRule.card_in_play(card)
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
                    condition = self._random_condition_with_compound()
            strategy.gain_priority.append(PriorityRule(card, condition))

        # Generate action priorities (only actual action cards)
        strategy.action_priority = []
        action_cards = list(self._kingdom_action_cards)
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
                        condition = self._random_condition_with_compound()
                strategy.action_priority.append(PriorityRule(card, condition))

        # Generate treasure priorities — include kingdom treasures
        treasure_list = list(self._kingdom_treasure_cards) + ["Gold", "Silver", "Copper"]
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

    def set_baseline_panel(self, panel: list[BaseStrategy]):
        """Set a panel of opponents. Games are split evenly across panel members,
        and fitness is the mean of per-opponent win rates. Overrides any single
        baseline set via set_baseline_strategy."""
        if not panel:
            raise ValueError("baseline panel cannot be empty")
        self._baseline_panel = list(panel)

    def _resolve_panel(self) -> list[BaseStrategy]:
        if self._baseline_panel:
            return self._baseline_panel
        if self._baseline_strategy is not None:
            return [self._baseline_strategy]
        big_money = self.battle_system.strategy_loader.get_strategy("Big Money")
        if not big_money:
            raise ValueError("Big Money strategy not found")
        return [big_money]

    def evaluate_strategy(self, strategy: BaseStrategy) -> float:
        """Evaluate a strategy by playing games against each panel opponent.
        Returns the mean win rate across the panel (0-100)."""
        try:
            panel = self._resolve_panel()
            from dominion.ai.genetic_ai import GeneticAI

            games_for_opp = _distribute_games(self.games_per_eval, len(panel))
            breakdown: list[tuple[str, float]] = []
            for i, opponent in enumerate(panel):
                games_per_opp = games_for_opp[i]
                kingdom_card_names = self.battle_system._determine_kingdom_cards(strategy, opponent)
                wins = 0
                for game_num in range(games_per_opp):
                    ai1 = GeneticAI(strategy)
                    ai2 = GeneticAI(opponent)
                    if game_num % 2 == 0:
                        winner, _s, _l, _t = self.battle_system.run_game(ai1, ai2, kingdom_card_names)
                    else:
                        winner, _s, _l, _t = self.battle_system.run_game(ai2, ai1, kingdom_card_names)
                    if winner == ai1:
                        wins += 1
                rate = wins / games_per_opp * 100
                breakdown.append((opponent.name, rate))
            self.last_eval_breakdown = breakdown
            return sum(r for _, r in breakdown) / len(breakdown)
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
        # Condition mutations: drop, replace, or fresh-from-none
        for priority in strategy.gain_priority:
            if random.random() < self.mutation_rate:
                if random.random() < 0.3:
                    if priority.condition is None:
                        # No condition — add one
                        if priority.card_name in ["Silver", "Gold", "Province"]:
                            cost = {"Silver": 3, "Gold": 6, "Province": 8}[priority.card_name]
                            priority.condition = PriorityRule.resources("coins", ">=", cost)
                        elif priority.card_name in self.kingdom_cards:
                            priority.condition = PriorityRule.turn_number("<=", random.randint(5, 15))
                        else:
                            priority.condition = self._random_condition_with_compound()
                    else:
                        # Existing condition — half the time drop it, half the time replace
                        if random.random() < 0.5:
                            priority.condition = None
                        else:
                            priority.condition = self._random_condition_with_compound()

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
                strategy.gain_priority.insert(pos, PriorityRule(card, self._random_condition_with_compound()))

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
                                priority.condition = self._random_condition_with_compound()

        # Add/remove action cards (only actual action cards)
        if random.random() < self.mutation_rate * 0.3:
            existing = {r.card_name for r in strategy.action_priority}
            missing = [c for c in self._kingdom_action_cards if c not in existing]
            if missing:
                card = random.choice(missing)
                pos = random.randint(0, len(strategy.action_priority))
                strategy.action_priority.insert(pos, PriorityRule(card, self._random_condition_with_compound()))

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
            for card_name in self._kingdom_treasure_cards:
                if card_name not in existing_treasures:
                    pos = random.randint(0, len(strategy.treasure_priority))
                    strategy.treasure_priority.insert(pos, PriorityRule(card_name))

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
    def _apply_fitness_sharing(
        population: list[BaseStrategy],
        raw_fitness: list[float],
        threshold: float = 0.8,
    ) -> list[float]:
        """Divide each individual's fitness by its niche count (members within
        ``threshold`` similarity, including itself). Clones lose to unique
        strategies at the same skill level."""
        shared: list[float] = []
        for i, individual in enumerate(population):
            niche = sum(
                1 for other in population
                if GeneticTrainer._strategy_similarity(individual, other) >= threshold
            )
            shared.append(raw_fitness[i] / max(1, niche))
        return shared

    @staticmethod
    def _strategy_similarity(a: BaseStrategy, b: BaseStrategy) -> float:
        """Top-5 gain card overlap as a fraction in [0, 1].
        Conditions are ignored — only card identity at the top of the buy menu matters.

        The divisor is the larger of the two effective top-rule counts (capped
        at 5), so identical small strategies (e.g. 3 rules each) still score
        1.0 instead of being artificially capped at 0.6 and dodging fitness
        sharing."""
        top_a = {r.card_name for r in a.gain_priority[:5]}
        top_b = {r.card_name for r in b.gain_priority[:5]}
        denom = max(1, min(5, max(len(top_a), len(top_b))))
        return len(top_a & top_b) / denom

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

    def create_next_generation(
        self,
        population: list[BaseStrategy],
        fitness_scores: list[float],
        selection_fitness: list[float] | None = None,
        immigrant_count: int = 0,
    ) -> list[BaseStrategy]:
        """Create the next generation through elitism, random immigrants, and
        crossover+mutation of selected parents.

        ``fitness_scores`` (raw) is used for elitism so the actual best individual
        always survives. ``selection_fitness`` (defaults to ``fitness_scores``)
        drives tournament selection — pass shared fitness here for diversity
        pressure. ``immigrant_count`` reserves that many slots for fresh
        randomly-generated strategies (genetic-drift breaker)."""
        if selection_fitness is None:
            selection_fitness = fitness_scores

        new_population: list[BaseStrategy] = []

        # Elite by raw fitness
        best_idx = fitness_scores.index(max(fitness_scores))
        new_population.append(deepcopy(population[best_idx]))

        # Random immigrants (capped to leave room for elite)
        immigrants = max(0, min(immigrant_count, self.population_size - 1))
        for _ in range(immigrants):
            new_population.append(self.create_random_strategy())

        # Fill remaining slots via tournament selection + crossover + mutation
        while len(new_population) < self.population_size:
            parent1 = self._tournament_select(population, selection_fitness)
            parent2 = self._tournament_select(population, selection_fitness)

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

                # Strip dead rules so mutation/crossover the next generation
                # operate on lean genomes. Behavior-preserving.
                if self.simplify_genomes:
                    from dominion.strategy.genome_simplification import (
                        simplify_strategy,
                    )
                    population = [simplify_strategy(s) for s in population]

                # Evaluate population
                fitness_scores = []
                for i, strategy in enumerate(population):
                    fitness = self.evaluate_strategy(strategy)
                    fitness_scores.append(fitness)

                    if fitness > best_fitness:
                        best_fitness = fitness
                        best_strategy = deepcopy(strategy)
                        log.info("New best fitness: %.2f", best_fitness)
                        if len(self.last_eval_breakdown) > 1:
                            parts = ", ".join(
                                f"{name}: {rate:.1f}%"
                                for name, rate in self.last_eval_breakdown
                            )
                            log.info("  panel breakdown — %s", parts)

                # Calculate generation statistics
                avg_fitness = sum(fitness_scores) / len(fitness_scores)

                # Update progress
                self.logger.update_training(gen, best_fitness, avg_fitness)

                # Diversity pressure: shared fitness for selection, random immigrants
                shared_fitness = self._apply_fitness_sharing(
                    population, fitness_scores, threshold=self.sharing_threshold
                )
                if self.population_size < 4 or self.immigrant_fraction <= 0:
                    immigrants = 0
                else:
                    immigrants = max(1, int(self.population_size * self.immigrant_fraction))

                population = self.create_next_generation(
                    population,
                    fitness_scores,
                    selection_fitness=shared_fitness,
                    immigrant_count=immigrants,
                )

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
