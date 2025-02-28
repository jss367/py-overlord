import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional

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
    cards_played: dict[str, int] = field(default_factory=dict)
    victory_points: dict[str, int] = field(default_factory=dict)
    actions_played: dict[str, int] = field(default_factory=dict)
    cards_bought: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_count": self.turn_count,
            "cards_played": dict(self.cards_played),
            "victory_points": dict(self.victory_points),
            "actions_played": dict(self.actions_played),
            "cards_bought": dict(self.cards_bought),
        }


class GameLogger:
    """Enhanced logging system for Dominion games."""

    def __init__(self, log_folder: str = "game_logs", log_frequency: int = 10):
        self.log_folder = log_folder
        self.log_frequency = log_frequency
        self.current_game_id: Optional[str] = None
        self.current_metrics = GameMetrics()
        self.game_logs: list[str] = []
        self.game_count = 0
        self.should_log_to_file = False
        self.training_progress: Optional[tqdm] = None

        # Create log directories
        os.makedirs(log_folder, exist_ok=True)
        os.makedirs(os.path.join(log_folder, "metrics"), exist_ok=True)

        # Set up file logger
        self._setup_file_logger()

    def _setup_file_logger(self):
        """Configure file logging with custom formatting."""
        self.file_logger = logging.getLogger("DominionGameFile")
        self.file_logger.setLevel(logging.DEBUG)

    def start_game(self, players: list[str]):
        """Start tracking a new game with enhanced initial state logging."""
        self.game_count += 1
        self.should_log_to_file = self.game_count % self.log_frequency == 0

        if self.should_log_to_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_game_id = f"game_{timestamp}"

            # Set up file handler for this game
            log_path = os.path.join(self.log_folder, f"{self.current_game_id}.log")
            file_handler = logging.FileHandler(log_path)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
            file_handler.setFormatter(formatter)
            self.file_logger.addHandler(file_handler)

            # Enhanced game start logging
            self.file_logger.info("=" * 60)
            self.file_logger.info(f"Starting Game {self.game_count}")
            self.file_logger.info(f"Players: {', '.join(players)}")
            self.file_logger.info("=" * 60)

    def format_player_name(self, name: str) -> str:
        """Format player name to be more readable."""
        if "GeneticAI-" in name:
            return f"AI-{name.split('-')[1][:4]}"  # Show only first 4 digits of id
        return name

    def log_turn_header(self, player_name: str, turn_number: int, resources: dict[str, int]):
        """Log formatted turn header with player state."""
        if not self.should_log_to_file:
            return

        self.file_logger.info("\n" + "=" * 40)
        self.file_logger.info(f"Turn {turn_number} - {self.format_player_name(player_name)}")
        self.file_logger.info(
            f"Resources: {resources['actions']} actions, " f"{resources['buys']} buys, " f"{resources['coins']} coins"
        )
        if resources.get("hand"):
            self.file_logger.info(f"Hand: {', '.join(resources['hand'])}")
        self.file_logger.info("-" * 40)

    def log_action(self, player_name: str, action: str, context: Optional[dict] = None):
        """Log game action with context."""
        if not self.should_log_to_file:
            return

        player = self.format_player_name(player_name)
        message = f"{player}: {action}"

        if context:
            details = []
            for key, value in context.items():
                if isinstance(value, list):
                    details.append(f"{key}: {', '.join(map(str, value))}")
                else:
                    details.append(f"{key}: {value}")
            if details:
                message += f" ({'; '.join(details)})"

        self.file_logger.info(message)

    def log_supply_change(self, card_name: str, count: int, remaining: int):
        """Log changes to the supply."""
        if not self.should_log_to_file:
            return

        self.file_logger.info(f"Supply: {card_name} {'gained' if count < 0 else 'added'} " f"({remaining} remaining)")

    def end_game(self, winner: str, scores: dict[str, int], supply_state: dict[str, int]):
        """End the current game with enhanced final state logging."""
        if self.should_log_to_file:
            # Log final game state
            self.file_logger.info("\n" + "=" * 60)
            self.file_logger.info("Game Over!")
            self.file_logger.info(f"Winner: {self.format_player_name(winner)}")
            self.file_logger.info("\nFinal Scores:")
            for player, score in scores.items():
                self.file_logger.info(f"  {self.format_player_name(player)}: {score}")

            self.file_logger.info("\nFinal Supply State:")
            for card, count in supply_state.items():
                if count == 0:
                    self.file_logger.info(f"  {card}: Empty")
                else:
                    self.file_logger.info(f"  {card}: {count} remaining")

            self.file_logger.info("=" * 60 + "\n")

            # Save metrics
            metrics_path = os.path.join(self.log_folder, "metrics", f"{self.current_game_id}_metrics.json")
            with open(metrics_path, "w") as f:
                json.dump(self.current_metrics.to_dict(), f, indent=2)

            # Remove file handler
            for handler in self.file_logger.handlers[:]:
                self.file_logger.removeHandler(handler)

        # Reset game state
        self.current_game_id = None
        self.current_metrics = GameMetrics()
        self.should_log_to_file = False

    def start_training(self, total_generations: int):
        """Initialize training progress tracking."""
        self.training_progress = tqdm(
            total=total_generations,
            desc="Training Progress",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} " "[{elapsed}<{remaining}, {rate_fmt}{postfix}]",
        )

    def update_training(self, generation: int, best_fitness: float, avg_fitness: float):
        """Update training progress information."""
        if self.training_progress:
            self.training_progress.update(1)
            self.training_progress.set_postfix(
                {
                    "Best Fitness": f"{best_fitness:.3f}",
                    "Avg Fitness": f"{avg_fitness:.3f}",
                    "Generation": generation + 1,
                }
            )

            # Log detailed metrics every 10 generations
            if generation % 10 == 0 and self.should_log_to_file:
                self.file_logger.info("\n" + "=" * 40)
                self.file_logger.info(f"Training Progress - Generation {generation + 1}")
                self.file_logger.info(f"Best Fitness: {best_fitness:.3f}")
                self.file_logger.info(f"Average Fitness: {avg_fitness:.3f}")
                self.file_logger.info("=" * 40)

    def end_training(self):
        """Clean up training progress tracking."""
        if self.training_progress:
            self.training_progress.close()
            self.training_progress = None

            if self.should_log_to_file:
                self.file_logger.info("\nTraining Complete!")
