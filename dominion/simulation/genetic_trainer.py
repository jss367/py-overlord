
# dominion/simulation/genetic_trainer.py
from typing import List, Tuple, Dict
import random
from ..ai.genetic_ai import GeneticAI, Strategy
from .game_runner import GameRunner
from .game_logger import GameLogger, LogLevel

class GeneticTrainer:
    """Trains Dominion strategies using a genetic algorithm."""
    
    def __init__(self, 
                 kingdom_cards: List[str],
                 population_size: int = 50,
                 generations: int = 100,
                 mutation_rate: float = 0.1,
                 games_per_eval: int = 10,
                 log_folder: str = "training_logs"):
        self.kingdom_cards = kingdom_cards
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.games_per_eval = games_per_eval
        self.game_runner = GameRunner(kingdom_cards, quiet=True)
        self.logger = GameLogger(log_folder, LogLevel.INFO)
        
    def train(self) -> Tuple[Strategy, Dict[str, float]]:
        """Run the genetic algorithm training process."""
        self.logger.log_info(
            f"Starting training with {self.population_size} strategies "
            f"for {self.generations} generations"
        )
        
        # Create initial population
        population = [
            Strategy.create_random(self.kingdom_cards) 
            for _ in range(self.population_size)
        ]
        
        best_strategy = None
        best_fitness = 0.0
        
        # Run generations
        for gen in range(self.generations):
            # Evaluate current population
            fitness_scores = self.evaluate_population(population)
            
            # Track best strategy
            max_fitness = max(fitness_scores)
            if max_fitness > best_fitness:
                best_fitness = max_fitness
                best_strategy = population[fitness_scores.index(max_fitness)]
            
            avg_fitness = sum(fitness_scores)/len(fitness_scores)
            self.logger.log_info(
                f"Generation {gen}: Best fitness = {max_fitness:.3f}, "
                f"Avg fitness = {avg_fitness:.3f}"
            )
            
            # Create next generation
            population = self.create_next_generation(population, fitness_scores)
            
        # Final evaluation of best strategy
        metrics = self.evaluate_strategy(best_strategy)
        
        self.logger.log_info("Training complete!")
        self.logger.log_info(f"Final metrics: {metrics}")
        self.logger.log_info("\nBest strategy card priorities:")
        for card, priority in best_strategy.gain_priorities.items():
            self.logger.log_info(f"{card}: {priority:.3f}")
        
        return best_strategy, metrics
        
    def evaluate_population(self, population: List[Strategy]) -> List[float]:
        """Evaluate fitness of all strategies in population."""
        return [self.evaluate_strategy(s)['win_rate'] for s in population]
        
    def evaluate_strategy(self, strategy: Strategy) -> Dict[str, float]:
        """Evaluate a single strategy by playing games."""
        ai = GeneticAI(strategy)
        wins = 0
        total_score = 0
        total_turns = 0
        
        # Play multiple games
        for _ in range(self.games_per_eval):
            # Create opponent with random strategy
            opponent = GeneticAI(Strategy.create_random(self.kingdom_cards))
            
            # Run game
            winner, scores = self.game_runner.run_game(ai, opponent)
            
            # Track results
            if winner == ai:
                wins += 1
            total_score += scores[ai.name]
            # Note: Would need to modify GameRunner to track turns
            
        return {
            'win_rate': wins / self.games_per_eval * 100,
            'avg_score': total_score / self.games_per_eval,
        }
        
    def create_next_generation(self, 
                             population: List[Strategy],
                             fitness_scores: List[float]) -> List[Strategy]:
        """Create new generation through selection, crossover, and mutation."""
        new_population = []
        
        # Sort strategies by fitness
        sorted_pop = [x for _, x in sorted(
            zip(fitness_scores, population),
            key=lambda pair: pair[0],
            reverse=True
        )]
        
        # Keep best strategies
        elite_count = max(1, self.population_size // 10)
        new_population.extend(sorted_pop[:elite_count])
        
        # Fill rest with crossover + mutation
        while len(new_population) < self.population_size:
            # Select parents
            parent1 = self.select_parent(sorted_pop)
            parent2 = self.select_parent(sorted_pop)
            
            # Create child through crossover
            child = Strategy.crossover(parent1, parent2)
            
            # Mutate
            child.mutate(self.mutation_rate)
            
            new_population.append(child)
            
        return new_population
        
    def select_parent(self, sorted_population: List[Strategy]) -> Strategy:
        """Select parent using tournament selection."""
        tournament_size = 3
        tournament = random.sample(sorted_population, tournament_size)
        return tournament[0]  # Already sorted by fitness

# Example usage
if __name__ == "__main__":
    # Example kingdom cards
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
        "Chapel"
    ]
    
    # Create trainer
    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=50,
        generations=100,
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
