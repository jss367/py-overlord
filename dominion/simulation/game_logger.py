from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import json
from enum import Enum, auto
import logging
from tqdm import tqdm

class LogLevel(Enum):
    DEBUG = auto()
    INFO = auto()
    WARN = auto()
    ERROR = auto()

@dataclass
class GameMetrics:
    """Tracks various game metrics."""
    turn_count: int = 0
    cards_played: Dict[str, int] = field(default_factory=dict)
    victory_points: Dict[str, int] = field(default_factory=dict)
    actions_played: Dict[str, int] = field(default_factory=dict)
    cards_bought: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'turn_count': self.turn_count,
            'cards_played': dict(self.cards_played),
            'victory_points': dict(self.victory_points),
            'actions_played': dict(self.actions_played),
            'cards_bought': dict(self.cards_bought),
        }

class GameLogger:
    """Logging system for Dominion games with minimal console output."""
    
    def __init__(self, 
                 log_folder: str = "game_logs",
                 log_frequency: int = 10):  # Log every Nth game
        self.log_folder = log_folder
        self.log_frequency = log_frequency
        self.current_game_id: Optional[str] = None
        self.current_metrics = GameMetrics()
        self.game_logs: List[str] = []
        self.game_count = 0
        self.should_log_to_file = False
        self.training_progress: Optional[tqdm] = None
        
        # Create log directories
        os.makedirs(log_folder, exist_ok=True)
        os.makedirs(os.path.join(log_folder, "metrics"), exist_ok=True)
        
        # Set up file logger for detailed logs
        self._setup_file_logger()
    
    def _setup_file_logger(self):
        """Configure file logging."""
        self.file_logger = logging.getLogger("DominionGameFile")
        self.file_logger.setLevel(logging.DEBUG)
        # Will add file handler when starting a game that should be logged
    
    def start_training(self, total_generations: int):
        """Initialize training progress bar."""
        self.training_progress = tqdm(total=total_generations, desc="Training Progress")

    def update_training(self, gen: int, best_fitness: float, avg_fitness: float):
        """Update training progress."""
        if self.training_progress:
            self.training_progress.update(1)
            self.training_progress.set_postfix({
                'Best Fitness': f'{best_fitness:.3f}',
                'Avg Fitness': f'{avg_fitness:.3f}'
            })
    
    def start_game(self, players: List[str]):
        """Start tracking a new game."""
        self.game_count += 1
        self.should_log_to_file = (self.game_count % self.log_frequency == 0)
        
        if self.should_log_to_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_game_id = f"game_{timestamp}"
            
            # Set up file handler for this game
            log_path = os.path.join(self.log_folder, f"{self.current_game_id}.log")
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.file_logger.addHandler(file_handler)
            
            # Log game start
            self.file_logger.info(f"Starting game {self.game_count} with players: {', '.join(players)}")
    
    def log_to_file(self, level: str, message: str):
        """Log message to file if this game should be logged."""
        if not self.should_log_to_file:
            return
            
        log_func = getattr(self.file_logger, level.lower())
        log_func(message)
    
    def log_game_event(self, message: str):
        """Log important game event to console."""
        # Only log major events to console, like game end or significant plays
        print(message)
    
    def end_game(self, winner: str, scores: Dict[str, int]):
        """End the current game and save metrics if needed."""
        if self.should_log_to_file:
            # Log final game state
            self.log_to_file("INFO", f"\nGame Over!\nWinner: {winner}")
            self.log_to_file("INFO", f"Final Scores: {scores}")
            
            # Save metrics
            metrics_path = os.path.join(
                self.log_folder, "metrics",
                f"{self.current_game_id}_metrics.json"
            )
            with open(metrics_path, 'w') as f:
                json.dump(self.current_metrics.to_dict(), f, indent=2)
            
            # Remove file handler
            for handler in self.file_logger.handlers[:]:
                self.file_logger.removeHandler(handler)
        
        # Reset game state
        self.current_game_id = None
        self.current_metrics = GameMetrics()
        self.should_log_to_file = False
    
    def end_training(self):
        """Close training progress bar."""
        if self.training_progress:
            self.training_progress.close()
            self.training_progress = None
