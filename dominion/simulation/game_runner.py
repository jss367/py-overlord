from typing import List, Tuple, Dict
from ..game.game_state import GameState
from ..ai.base_ai import AI
from ..cards.registry import get_card
from .game_logger import GameLogger, LogLevel

class GameRunner:
    """Runs Dominion games between AIs."""
    
    def __init__(self, kingdom_cards: List[str], quiet: bool = True, log_folder: str = "game_logs"):
        self.kingdom_cards = kingdom_cards
        self.quiet = quiet
        self.logger = GameLogger(
            log_folder=log_folder,
            log_level=LogLevel.INFO if not quiet else LogLevel.ERROR
        )
        
    def run_game(self, ai1: AI, ai2: AI) -> Tuple[AI, Dict[str, int]]:
        """Run a single game between two AIs and return winner and scores."""
        # Start game logging
        self.logger.start_game(
            players=[ai1.name, ai2.name],
            kingdom_cards=self.kingdom_cards
        )
        
        # Set up game state
        game_state = GameState(
            players=[],  # Will be created with AIs
            supply={},   # Will be set up with cards
        )
        
        # Set up logging callback
        game_state.log_callback = self.logger.log_info
        
        # Add kingdom cards to supply
        kingdom_cards = [get_card(name) for name in self.kingdom_cards]
        
        # Initialize game with AIs
        game_state.initialize_game([ai1, ai2], kingdom_cards)
        
        # Run game until completion
        while not game_state.is_game_over():
            game_state.play_turn()
            
            # Log deck compositions after cleanup
            if game_state.phase == "cleanup":
                for player in game_state.players:
                    deck_composition = {}
                    for pile in [player.deck, player.hand, player.discard, player.in_play]:
                        for card in pile:
                            deck_composition[card.name] = deck_composition.get(card.name, 0) + 1
                    self.logger.log_deck_composition(player.ai.name, deck_composition)
        
        # Get results
        scores = {p.ai.name: p.get_victory_points(game_state) for p in game_state.players}
        winner = max(game_state.players, key=lambda p: p.get_victory_points(game_state)).ai
        
        # End game logging
        self.logger.end_game(
            winner=winner.name,
            scores=scores,
            final_supply=dict(game_state.supply)
        )
        
        return winner, scores
    
    def _log_message(self, message: str):
        """Callback for game state logging."""
        self.logger.log_message(message)
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
