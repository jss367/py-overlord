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
        
        # Initialize game with AIs (not PlayerStates)
        game_state.initialize_game([ai1, ai2], kingdom_cards)
        
        if not self.quiet:
            print(f"\nStarting game: {ai1.name} vs {ai2.name}")
        
        # Run game until completion
        while not self.is_game_over(game_state):
            game_state.play_turn()
        
        # Get results
        scores = {p.ai.name: p.get_victory_points(game_state) for p in game_state.players}
        winner = max(game_state.players, key=lambda p: p.get_victory_points(game_state)).ai
        
        if not self.quiet:
            print(f"\nGame over!")
            print(f"Scores: {scores}")
            print(f"Winner: {winner.name}")
        
        return winner, scores

    def is_game_over(self, game_state: GameState) -> bool:
        """Check if the game is over."""
        # Game ends if Province pile is empty
        if game_state.supply.get("Province", 0) == 0:
            return True
            
        # Or if any three supply piles are empty
        empty_piles = sum(1 for count in game_state.supply.values() if count == 0)
        return empty_piles >= 3
