from typing import List, Tuple, Dict, Optional
from ..game.game_state import GameState
from ..ai.base_ai import AI
from ..cards.registry import get_card
from .game_logger import GameLogger


class GameRunner:
    """Runs Dominion games between AIs."""

    def __init__(self, kingdom_cards: List[str], logger: Optional[GameLogger] = None):
        self.kingdom_cards = kingdom_cards
        self.logger = logger or GameLogger()

    def run_game(self, ai1: AI, ai2: AI) -> Tuple[AI, Dict[str, int]]:
        """Run a single game between two AIs and return winner and scores."""
        # Start game logging
        self.logger.start_game([ai1.name, ai2.name])

        # Set up game state
        game_state = GameState(players=[], supply={})
        # Update to use the correct logging method
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

    def is_game_over(self, game_state: GameState) -> bool:
        """Check if the game is over."""
        # Game ends if Province pile is empty
        if game_state.supply.get("Province", 0) == 0:
            return True

        # Or if any three supply piles are empty
        empty_piles = sum(1 for count in game_state.supply.values() if count == 0)
        return empty_piles >= 3
