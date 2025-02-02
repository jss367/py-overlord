from typing import Optional
from dominion.game.game_state import GameState
from dominion.ai.base_ai import AI
from dominion.cards.registry import get_card
from dominion.simulation.game_logger import GameLogger
from typing import Union
from pathlib import Path
from dominion.ai.genetic_ai import GeneticAI
from dominion.strategy.strategy import Strategy as GeneticStrategy
from dominion.strategy.strategy_ai import StrategyAI
from dominion.strategy.strategy_parser import StrategyLoader
from dominion.strategy.strategy_runner import StrategyRunner


class GameRunner:
    """Runs Dominion games between AIs."""

    def __init__(self, kingdom_cards: list[str], logger: Optional[GameLogger] = None):
        self.kingdom_cards = kingdom_cards
        self.logger = logger or GameLogger()

        # Initialize strategy loader
        self.strategy_loader = StrategyLoader()
        strategies_dir = Path("strategies")
        if strategies_dir.exists():
            self.strategy_loader.load_directory(strategies_dir)

    def create_ai(self, strategy: Union[str, GeneticStrategy]) -> AI:
        """Create an AI from either a strategy name (YAML) or GeneticStrategy"""
        if not isinstance(strategy, str):
            # Use genetic strategy
            return GeneticAI(strategy)
        # Load YAML strategy
        yaml_strategy = self.strategy_loader.get_strategy(strategy)
        runner = StrategyRunner(yaml_strategy)
        return StrategyAI(runner)

    def run_game(
        self,
        strategy1: Union[str, GeneticStrategy],
        strategy2: Union[str, GeneticStrategy],
    ) -> tuple[AI, dict[str, int]]:
        """Run a single game between two strategies and return winner and scores."""
        # Create AIs from strategies
        ai1 = self.create_ai(strategy1)
        ai2 = self.create_ai(strategy2)

        # Start game logging
        self.logger.start_game([ai1.name, ai2.name])

        # Set up game state
        game_state = GameState(players=[], supply={})
        game_state.log_callback = lambda msg: (
            self.logger.file_logger.info(msg)
            if self.logger.should_log_to_file
            else print(msg)
        )

        # Initialize game
        kingdom_cards = [get_card(name) for name in self.kingdom_cards]
        game_state.initialize_game([ai1, ai2], kingdom_cards)

        # Run game
        while not game_state.is_game_over():
            game_state.play_turn()

        # Get results
        scores = {
            p.ai.name: p.get_victory_points(game_state) for p in game_state.players
        }
        winner = max(
            game_state.players, key=lambda p: p.get_victory_points(game_state)
        ).ai

        # End game logging
        self.logger.end_game(winner.name, scores, game_state.supply)

        return winner, scores

    def _log_message(self, message: str):
        """Callback for game state logging."""
        if self.logger and self.logger.should_log_to_file:
            self.logger.file_logger.info(message)
        if not self.quiet:
            print(message)
