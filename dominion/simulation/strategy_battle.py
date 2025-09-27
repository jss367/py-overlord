import argparse
import logging
from logging import getLogger
from typing import Any, Optional

try:  # pragma: no cover - optional dependency for nicer logging
    import coloredlogs
except ImportError:  # pragma: no cover
    coloredlogs = None

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import BoardConfig
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.projects.registry import get_project
from dominion.ways.registry import get_way
from dominion.game.game_state import GameState
from dominion.simulation.game_logger import GameLogger
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategy_loader import StrategyLoader

logger = getLogger(__name__)

if coloredlogs:  # pragma: no cover - harmless when library unavailable
    coloredlogs.install(level="INFO", logger=logger)

DEFAULT_KINGDOM_CARDS = [
    "Village",
    "Smithy",
    "Market",
    "Festival",
    "Laboratory",
    "Mine",
    "Witch",
    "Moat",
    "Workshop",
    "Chapel",
]

# Cards that should not be included in the kingdom supply when extracting
# names from strategies. These are part of the base supply or starting cards
# and are automatically handled by ``GameState.setup_supply``.
BASIC_CARDS = {
    "Copper",
    "Silver",
    "Gold",
    "Estate",
    "Duchy",
    "Province",
    "Curse",
    # Shelters are never part of the normal supply
    "Hovel",
    "Necropolis",
    "Overgrown Estate",
}

# Set up module-level logger
logger = logging.getLogger(__name__)


class StrategyBattle:
    """System for running battles between strategies."""

    def __init__(
        self,
        kingdom_cards: Optional[list[str]] = None,
        log_folder: str = "battle_logs",
        use_shelters: bool = False,
        board_config: Optional[BoardConfig] = None,
    ):
        # ``kingdom_cards`` allows explicitly providing the supply. If omitted
        # the supply will be dynamically determined from the strategies used in
        # each battle.
        self.board_config = board_config
        if board_config and kingdom_cards and board_config.kingdom_cards != kingdom_cards:
            raise ValueError("kingdom_cards and board_config.kingdom_cards must match when both provided")

        self.kingdom_cards = board_config.kingdom_cards if board_config else kingdom_cards
        self.logger = GameLogger(log_folder=log_folder)
        self.strategy_loader = StrategyLoader()  # Now automatically loads all strategies
        self.use_shelters = use_shelters

    def _extract_cards_from_strategy(self, strat: EnhancedStrategy) -> set[str]:
        """Return all card names referenced by a strategy's priority lists."""
        cards: set[str] = set()
        for priority_list in [
            strat.gain_priority,
            strat.action_priority,
            strat.trash_priority,
            strat.treasure_priority,
        ]:
            for rule in priority_list:
                if isinstance(rule, PriorityRule):
                    cards.add(rule.card_name)
        return cards

    def _determine_kingdom_cards(self, strat1: EnhancedStrategy, strat2: EnhancedStrategy) -> list[str]:
        """Compute kingdom cards from both strategies if not explicitly set."""
        if self.kingdom_cards is not None:
            return self.kingdom_cards

        all_cards = self._extract_cards_from_strategy(strat1) | self._extract_cards_from_strategy(strat2)
        return sorted(c for c in all_cards if c not in BASIC_CARDS)

    def _prepare_board_components(self, kingdom_card_names: list[str]):
        """Instantiate cards and landscape components for a game."""

        kingdom_cards = [get_card(name) for name in kingdom_card_names]

        events = []
        projects = []
        ways = []

        if self.board_config:
            events = [get_event(name) for name in self.board_config.events]
            projects = [get_project(name) for name in self.board_config.projects]
            ways = [get_way(name) for name in self.board_config.ways]

        return kingdom_cards, events, projects, ways

    def run_battle(self, strategy1_name: str, strategy2_name: str, num_games: int = 100) -> dict[str, Any]:
        """Run multiple games between two strategies"""
        # Get strategies from loader
        strategy1 = self.strategy_loader.get_strategy(strategy1_name)
        strategy2 = self.strategy_loader.get_strategy(strategy2_name)

        missing = []
        if not strategy1:
            missing.append(strategy1_name)
        if not strategy2:
            missing.append(strategy2_name)
        if missing:
            logger.warning("Could not find strategies: %s", ', '.join(missing))
            raise ValueError(f"Could not find strategies: {', '.join(missing)}")

        # Initialize results tracking
        results = {
            "strategy1_name": strategy1_name,
            "strategy2_name": strategy2_name,
            "strategy1_wins": 0,
            "strategy2_wins": 0,
            "strategy1_total_score": 0,
            "strategy2_total_score": 0,
            "games_played": num_games,
            "detailed_results": [],
        }

        # Run the games
        logger.info("\nRunning %d games between:", num_games)
        logger.info("Strategy 1: %s", strategy1_name)
        logger.info("Strategy 2: %s\n", strategy2_name)

        kingdom_card_names = self._determine_kingdom_cards(strategy1, strategy2)
        logger.info("Using kingdom cards: %s", ", ".join(kingdom_card_names))

        if self.board_config:
            logger.info(
                "Board configuration: %s",
                ", ".join(
                    filter(
                        None,
                        [
                            f"Ways={len(self.board_config.ways)}" if self.board_config.ways else "",
                            f"Projects={len(self.board_config.projects)}" if self.board_config.projects else "",
                            f"Events={len(self.board_config.events)}" if self.board_config.events else "",
                        ],
                    ),
                )
                or "(no landscapes)",
            )

        for game_num in range(num_games):
            logger.info("Playing game %d/%d...", game_num + 1, num_games)

            # Create fresh AIs for each game using new strategy instances
            ai1 = GeneticAI(strategy1)
            ai2 = GeneticAI(strategy2)

            # Alternate who goes first
            if game_num % 2 == 0:
                winner, scores, log_path, turns = self.run_game(ai1, ai2, kingdom_card_names)
            else:
                winner, scores, log_path, turns = self.run_game(ai2, ai1, kingdom_card_names)

            # Record results
            game_result = {
                "game_number": game_num + 1,
                "winner": strategy1_name if winner == ai1 else strategy2_name,
                "strategy1_score": scores[ai1.name],
                "strategy2_score": scores[ai2.name],
                "margin": abs(scores[ai1.name] - scores[ai2.name]),
                "turns": turns,
                "log_path": log_path,
            }
            results["detailed_results"].append(game_result)

            if winner == ai1:
                results["strategy1_wins"] += 1
            else:
                results["strategy2_wins"] += 1

            results["strategy1_total_score"] += scores[ai1.name]
            results["strategy2_total_score"] += scores[ai2.name]

        # Calculate final statistics
        results["strategy1_win_rate"] = results["strategy1_wins"] / num_games * 100
        results["strategy2_win_rate"] = results["strategy2_wins"] / num_games * 100
        results["strategy1_avg_score"] = results["strategy1_total_score"] / num_games
        results["strategy2_avg_score"] = results["strategy2_total_score"] / num_games

        results["log_paths"] = list(self.logger.game_logs)

        return results

    def run_game(
        self,
        ai1: GeneticAI,
        ai2: GeneticAI,
        kingdom_card_names: list[str],
    ) -> tuple[GeneticAI, dict[str, int], Optional[str], int]:
        """Run a single game between two AIs. TODO: This shouldn't be within this class."""
        # Start game logging with actual AI objects for better descriptions
        self.logger.start_game([ai1, ai2])

        # Set up game state and attach logger for structured logging
        game_state = GameState(players=[], supply={})
        game_state.set_logger(self.logger)

        # Initialize game
        kingdom_cards, events, projects, ways = self._prepare_board_components(kingdom_card_names)
        game_state.initialize_game(
            [ai1, ai2],
            kingdom_cards,
            use_shelters=self.use_shelters,
            events=events,
            projects=projects,
            ways=ways,
        )

        # Run game
        while not game_state.is_game_over():
            game_state.play_turn()

        # Get results
        final_turns = game_state.turn_number
        scores = {p.ai.name: p.get_victory_points(game_state) for p in game_state.players}
        winner = max(game_state.players, key=lambda p: p.get_victory_points(game_state)).ai

        # End game logging and capture log path if any
        log_path = self.logger.end_game(winner.name, scores, game_state.supply, game_state.players)

        return winner, scores, log_path, final_turns


def main():
    parser = argparse.ArgumentParser(description="Run a battle between two Dominion strategies")
    parser.add_argument("strategy1_name", help="Name of first strategy")
    parser.add_argument("strategy2_name", help="Name of second strategy")
    parser.add_argument("--games", type=int, default=100, help="Number of games to play")
    parser.add_argument(
        "--use-shelters",
        action="store_true",
        help="Start games with Shelters instead of Estates",
    )
    args = parser.parse_args()

    logger.info("\nInitializing battle between %s and %s...", args.strategy1_name, args.strategy2_name)

    battle = StrategyBattle(use_shelters=args.use_shelters)

    # Print available strategies
    logger.info("\nAvailable strategies: %s", ", ".join(battle.strategy_loader.list_strategies()))

    logger.info("\nRunning %d games...", args.games)
    results = battle.run_battle(args.strategy1_name, args.strategy2_name, args.games)

    if results:
        print_results(results)
    else:
        logger.error("\nError: No results generated from battle")


def print_results(results: dict[str, Any]):
    """Print battle results in a readable format."""
    logger.info("\n=== Strategy Battle Results ===")
    logger.info("\nGames played: %d", results['games_played'])

    logger.info("\n%s:", results['strategy1_name'])
    logger.info("  Wins: %d (%.1f%%)", results['strategy1_wins'], results['strategy1_win_rate'])
    logger.info("  Average Score: %.1f", results['strategy1_avg_score'])

    logger.info("\n%s:", results['strategy2_name'])
    logger.info("  Wins: %d (%.1f%%)", results['strategy2_wins'], results['strategy2_win_rate'])
    logger.info("  Average Score: %.1f", results['strategy2_avg_score'])

    logger.info("\nDetailed game results:")
    for game in results["detailed_results"]:
        logger.info("\nGame %d:", game['game_number'])
        logger.info("  Winner: %s", game['winner'])
        logger.info(
            "  Scores: %s=%d, %s=%d",
            results['strategy1_name'],
            game['strategy1_score'],
            results['strategy2_name'],
            game['strategy2_score'],
        )
        logger.info("  Margin: %d", game['margin'])
        logger.info("  Turns: %d", game['turns'])
        if game.get("log_path"):
            logger.info("  Log: %s", game['log_path'])


if __name__ == "__main__":
    main()
