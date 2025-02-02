import random

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class GeneticTrainer:
    """Trains Dominion strategies using a genetic algorithm."""

    def create_random_strategy(self) -> EnhancedStrategy:
        """Create a random strategy with smart defaults"""
        strategy = EnhancedStrategy()
        strategy.name = f"Generated-{id(strategy)}"

        # Add basic action priorities
        strategy.action_priority = [
            PriorityRule("Chapel"),  # Early game priority
            PriorityRule("Village", "my.actions < 2"),  # Need actions
            PriorityRule("Laboratory"),  # Always good
            PriorityRule("Smithy", "my.actions >= 1"),  # If we have actions
            PriorityRule("Market"),  # Flexible card
        ]

        # Add basic gain priorities
        strategy.gain_priority = [
            PriorityRule("Province", "my.coins >= 8"),
            PriorityRule("Gold", "my.coins >= 6"),
            PriorityRule("Silver", "my.coins >= 3"),
            PriorityRule("Laboratory", "state.turn_number() <= 12"),
            PriorityRule("Village", "state.turn_number() <= 10"),
        ]

        # Add trash priorities
        strategy.trash_priority = [
            PriorityRule("Curse"),  # Always trash
            PriorityRule("Copper", "my.countInDeck('Silver') >= 3"),
            PriorityRule("Estate", "state.turn_number() <= 10"),
        ]

        # Add treasure priorities
        strategy.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        return strategy

    def mutate_strategy(self, strategy: EnhancedStrategy, mutation_rate: float) -> EnhancedStrategy:
        """Create a mutated copy of the strategy"""
        new_strategy = EnhancedStrategy()
        new_strategy.name = f"Mutated-{strategy.name}"

        def mutate_rules(rules: list[PriorityRule]) -> list[PriorityRule]:
            mutated = []
            for rule in rules:
                if random.random() < mutation_rate:
                    # Possible mutations:
                    # 1. Remove condition
                    # 2. Add condition
                    # 3. Modify condition
                    # 4. Change position
                    if rule.condition and random.random() < 0.3:
                        # Remove condition
                        mutated.append(PriorityRule(rule.card_name))
                    elif not rule.condition and random.random() < 0.3:
                        # Add condition
                        conditions = [
                            "my.actions < 2",
                            "my.coins >= 6",
                            "state.turn_number() <= 10",
                            f"my.countInDeck('{rule.card_name}') < 2",
                        ]
                        mutated.append(PriorityRule(rule.card_name, random.choice(conditions)))
                    else:
                        # Keep as is
                        mutated.append(rule)
                else:
                    mutated.append(rule)

            # Randomly shuffle a portion of the list
            if random.random() < mutation_rate:
                split_point = random.randint(0, len(mutated))
                shuffled_portion = mutated[split_point:]
                random.shuffle(shuffled_portion)
                mutated = mutated[:split_point] + shuffled_portion

            return mutated

        # Mutate each priority list
        new_strategy.action_priority = mutate_rules(strategy.action_priority)
        new_strategy.gain_priority = mutate_rules(strategy.gain_priority)
        new_strategy.trash_priority = mutate_rules(strategy.trash_priority)
        new_strategy.treasure_priority = mutate_rules(strategy.treasure_priority)

        return new_strategy

    def crossover(self, parent1: EnhancedStrategy, parent2: EnhancedStrategy) -> EnhancedStrategy:
        """Create a new strategy by combining two parents"""
        child = EnhancedStrategy()

        def crossover_rules(rules1: list[PriorityRule], rules2: list[PriorityRule]) -> list[PriorityRule]:
            crossover_point = random.randint(0, min(len(rules1), len(rules2)))
            return rules1[:crossover_point] + rules2[crossover_point:]

        # Crossover each priority list
        child.action_priority = crossover_rules(parent1.action_priority, parent2.action_priority)
        child.gain_priority = crossover_rules(parent1.gain_priority, parent2.gain_priority)
        child.trash_priority = crossover_rules(parent1.trash_priority, parent2.trash_priority)
        child.treasure_priority = crossover_rules(parent1.treasure_priority, parent2.treasure_priority)

        return child
