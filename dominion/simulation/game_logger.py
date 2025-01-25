from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import json
from enum import Enum, auto
import logging

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
    treasures_played: Dict[str, int] = field(default_factory=dict)
    cards_bought: Dict[str, int] = field(default_factory=dict)
    deck_compositions: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary for serialization."""
        return {
            'turn_count': self.turn_count,
            'cards_played': dict(self.cards_played),
            'victory_points': dict(self.victory_points),
            'actions_played': dict(self.actions_played),
            'treasures_played': dict(self.treasures_played),
            'cards_bought': dict(self.cards_bought),
            'deck_compositions': {
                player: dict(cards) 
                for player, cards in self.deck_compositions.items()
            }
        }

class GameLogger:
    """Enhanced logging system for Dominion games."""
    
    def __init__(self, 
                 log_folder: str = "game_logs",
                 log_level: LogLevel = LogLevel.INFO,
                 log_format: str = "%(asctime)s - %(levelname)s - %(message)s"):
        self.log_folder = log_folder
        self.log_level = log_level
        self.current_game_id: Optional[str] = None
        self.current_metrics = GameMetrics()
        self.game_logs: List[str] = []
        
        # Set up logging
        self._setup_logging(log_format)
        
        # Create log directories
        os.makedirs(log_folder, exist_ok=True)
        os.makedirs(os.path.join(log_folder, "metrics"), exist_ok=True)
        os.makedirs(os.path.join(log_folder, "game_logs"), exist_ok=True)
    
    def _setup_logging(self, log_format: str):
        """Configure logging system."""
        self.logger = logging.getLogger("DominionGame")
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._get_logging_level())
        console_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(console_handler)
    
    def _get_logging_level(self) -> int:
        """Convert LogLevel enum to logging module level."""
        return {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARN: logging.WARNING,
            LogLevel.ERROR: logging.ERROR
        }[self.log_level]
    
    def start_game(self, players: List[str], kingdom_cards: List[str]):
        """Start tracking a new game."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_game_id = f"game_{timestamp}"
        self.current_metrics = GameMetrics()
        self.game_logs = []
        
        # Log game start
        start_msg = (
            f"\n{'='*60}\n"
            f"Starting new game at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Players: {', '.join(players)}\n"
            f"Kingdom cards: {', '.join(kingdom_cards)}\n"
            f"{'='*60}\n"
        )
        self.log_info(start_msg)
    
    def log_debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
        self._add_to_game_log("DEBUG", message)
    
    def log_info(self, message: str):
        """Log info message."""
        self.logger.info(message)
        self._add_to_game_log("INFO", message)
    
    def log_warn(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
        self._add_to_game_log("WARN", message)
    
    def log_error(self, message: str):
        """Log error message."""
        self.logger.error(message)
        self._add_to_game_log("ERROR", message)
    
    def _add_to_game_log(self, level: str, message: str):
        """Add message to current game log."""
        if self.current_game_id:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.game_logs.append(f"[{timestamp}] {level}: {message}")
    
    def log_turn(self, player: str, turn_number: int, phase: str):
        """Log turn information."""
        self.log_info(f"\n--- {player}'s Turn {turn_number} ({phase} phase) ---")
        self.current_metrics.turn_count = max(self.current_metrics.turn_count, turn_number)
    
    def log_action_played(self, player: str, card_name: str):
        """Log when an action card is played."""
        self.log_debug(f"{player} plays {card_name}")
        self.current_metrics.cards_played[card_name] = (
            self.current_metrics.cards_played.get(card_name, 0) + 1
        )
        self.current_metrics.actions_played[player] = (
            self.current_metrics.actions_played.get(player, 0) + 1
        )
    
    def log_treasure_played(self, player: str, card_name: str):
        """Log when a treasure is played."""
        self.log_debug(f"{player} plays {card_name}")
        self.current_metrics.treasures_played[player] = (
            self.current_metrics.treasures_played.get(player, 0) + 1
        )
    
    def log_card_bought(self, player: str, card_name: str):
        """Log when a card is bought."""
        self.log_debug(f"{player} buys {card_name}")
        self.current_metrics.cards_bought[card_name] = (
            self.current_metrics.cards_bought.get(card_name, 0) + 1
        )
    
    def log_deck_composition(self, player: str, deck_contents: Dict[str, int]):
        """Log current deck composition for a player."""
        self.current_metrics.deck_compositions[player] = deck_contents
    
    def end_game(self, winner: str, scores: Dict[str, int], final_supply: Dict[str, int]):
        """End the current game and save logs/metrics."""
        if not self.current_game_id:
            return
            
        # Update final victory points
        self.current_metrics.victory_points = scores
        
        # Log game end summary
        end_summary = (
            f"\n{'='*60}\n"
            f"Game Over!\n"
            f"Winner: {winner}\n"
            f"Final Scores: {scores}\n"
            f"Remaining Supply: {final_supply}\n"
            f"Total Turns: {self.current_metrics.turn_count}\n"
            f"{'='*60}\n"
        )
        self.log_info(end_summary)
        
        # Save detailed game log
        log_path = os.path.join(
            self.log_folder, "game_logs",
            f"{self.current_game_id}.log"
        )
        with open(log_path, 'w') as f:
            f.write('\n'.join(self.game_logs))
        
        # Save metrics
        metrics_path = os.path.join(
            self.log_folder, "metrics",
            f"{self.current_game_id}_metrics.json"
        )
        with open(metrics_path, 'w') as f:
            json.dump(self.current_metrics.to_dict(), f, indent=2)
        
        # Clear current game data
        self.current_game_id = None
        self.game_logs = []
        self.current_metrics = GameMetrics()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current game metrics."""
        if not self.current_game_id:
            return {}
        return self.current_metrics.to_dict()
