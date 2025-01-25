import os
from datetime import datetime
from typing import Dict, List, Optional, Any

class GameLogger:
    """Handles detailed logging of Dominion games."""
    
    def __init__(self, log_folder: str = "game_logs"):
        self.log_folder = log_folder
        self.game_count = 0
        self.current_log: List[str] = []
        self.should_log = False
        
        # Create log directory if it doesn't exist
        os.makedirs(log_folder, exist_ok=True)
    
    def start_game(self):
        """Start tracking a new game."""
        self.game_count += 1
        self.should_log = (self.game_count % 10 == 0)  # Log every 10th game
        self.current_log = []
        
        if self.should_log:
            self.log_game_start()
    
    def log_game_start(self):
        """Log the start of a game."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_log.append(f"Game {self.game_count} - Started at {timestamp}")
        self.current_log.append("-" * 50)
    
    def log_message(self, message: str):
        """Add a message to the current game log if logging is enabled."""
        if self.should_log:
            self.current_log.append(message)
    
    def end_game(self, winner_name: str, scores: Dict[str, int], metrics: Optional[Dict[str, Any]] = None):
        """End the current game and write log to file if enabled."""
        if not self.should_log:
            return
            
        # Add game results
        self.current_log.append("\nGame Results:")
        self.current_log.append(f"Winner: {winner_name}")
        self.current_log.append("Scores:")
        for player, score in scores.items():
            self.current_log.append(f"  {player}: {score}")
            
        # Add any additional metrics
        if metrics:
            self.current_log.append("\nGame Metrics:")
            for key, value in metrics.items():
                self.current_log.append(f"  {key}: {value}")
        
        # Write to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_{self.game_count}_{timestamp}.log"
        filepath = os.path.join(self.log_folder, filename)
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(self.current_log))
            
        # Clear current log
        self.current_log = []
