
# dominion/simulation/game_runner.py
from typing import List, Tuple, Dict, Optional
from ..game.game_state import GameState
from ..ai.base_ai import AI
from ..cards.registry import get_card

class GameRunner:
    """Runs Dominion games between AIs."""
    
    def __init__(self, kingdom_cards: List[str], quiet: bool = True):
        self.kingdom_cards = kingdom_cards
        self.quiet = quiet
        
    def run_game(self, ai1: AI, ai2: AI) -> Tuple[AI, Dict[str, int]]:
        """Run a single game between two AIs and return winner and scores."""
        # Set up game state
        game_state = GameState(
            players=[],  # Will be created with AIs
            supply={},   # Will be set up with cards
        )
        
        # Add kingdom cards to supply
        kingdom_cards = [get_card(name) for name in self.kingdom_cards]
        game_state.initialize_game([ai1, ai2], kingdom_cards)
        
        if not self.quiet:
            print(f"\nStarting game: {ai1.name} vs {ai2.name}")
        
        # Run game until completion
        while not game_state.game_is_over():
            game_state.play_turn()
        
        # Get results
        scores = {p.ai.name: p.get_victory_points(game_state) for p in game_state.players}
        winner = max(game_state.players, key=lambda p: p.get_victory_points(game_state)).ai
        
        if not self.quiet:
            print(f"\nGame over!")
            print(f"Scores: {scores}")
            print(f"Winner: {winner.name}")
        
        return winner, scores
