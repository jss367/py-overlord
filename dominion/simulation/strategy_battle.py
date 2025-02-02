import argparse
from pathlib import Path
from typing import Any, dict

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.simulation.game_logger import GameLogger
from dominion.strategy.strategy_ai import StrategyAI
from dominion.strategy.strategy_parser import StrategyLoader
from dominion.strategy.strategy_runner import StrategyRunner


class StrategyBattle:
    """System for running battles between YAML-defined strategies."""

    def __init__(self, kingdom_cards: list[str], log_folder: str = "battle_logs"):
        self.kingdom_cards = kingdom_cards
        self.logger = GameLogger(log_folder=log_folder)

        # Load all available strategies
        self.strategy_loader = StrategyLoader()
        strategies_dir = Path("strategies")
        if strategies_dir.exists():
            self.strategy_loader.load_directory(strategies_dir)
        else:
            raise FileNotFoundError("Strategies directory not found")

    def run_battle(self, strategy1_name: str, strategy2_name: str, num_games: int = 100) -> dict[str, Any]:
        """Run multiple games between two strategies."""
        # Validate strategies exist
        if strategy1_name not in self.strategy_loader.strategies:
            raise ValueError(f"Strategy not found: {strategy1_name}")
        if strategy2_name not in self.strategy_loader.strategies:
            raise ValueError(f"Strategy not found: {strategy2_name}")

        # Validate required kingdom cards are available
        strategy1 = self.strategy_loader.get_strategy(strategy1_name)
        strategy2 = self.strategy_loader.get_strategy(strategy2_name)

        required_cards = set(strategy1.requires + strategy2.requires)
        missing_cards = required_cards - set(self.kingdom_cards)
        if missing_cards:
            raise ValueError(f"Missing required kingdom cards: {missing_cards}")

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
        print(f"\nRunning {num_games} games between:")
        print(f"Strategy 1: {strategy1_name}")
        print(f"Strategy 2: {strategy2_name}\n")

        for game_num in range(num_games):
            print(f"Playing game {game_num + 1}/{num_games}...")

            # Create fresh AIs for each game
            ai1 = StrategyAI(StrategyRunner(strategy1))
            ai2 = StrategyAI(StrategyRunner(strategy2))

            # Alternate who goes first
            if game_num % 2 == 0:
                winner, scores = self._run_game(ai1, ai2)
            else:
                winner, scores = self._run_game(ai2, ai1)

            # Record results
            game_result = {
                "game_number": game_num + 1,
                "winner": strategy1_name if winner == ai1 else strategy2_name,
                "strategy1_score": scores[ai1.name],
                "strategy2_score": scores[ai2.name],
                "margin": abs(scores[ai1.name] - scores[ai2.name]),
                "turns": self.logger.current_metrics.turn_count,
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

        return results

    def _run_game(self, ai1: StrategyAI, ai2: StrategyAI) -> tuple[StrategyAI, dict[str, int]]:
        """Run a single game between two AIs."""
        # Start game logging
        self.logger.start_game([ai1.name, ai2.name])

        # Set up game state
        game_state = GameState(players=[], supply={})
        game_state.log_callback = lambda msg: (
            self.logger.file_logger.info(msg) if self.logger.should_log_to_file else print(msg)
        )

        # Initialize game
        kingdom_cards = [get_card(name) for name in self.kingdom_cards]
        game_state.initialize_game([ai1, ai2], kingdom_cards)

        # Run game
        while not game_state.is_game_over():
            game_state.play_turn()

        # Get results
        scores = {p.ai.name: p.get_victory_points(game_state) for p in game_state.players}
        winner = max(game_state.players, key=lambda p: p.get_victory_points(game_state)).ai

        # End game logging
        self.logger.end_game(winner.name, scores, game_state.supply)

        return winner, scores


def print_results(results: dict[str, Any]):
    """Print battle results in a readable format."""
    print("\n=== Strategy Battle Results ===")
    print(f"\nGames played: {results['games_played']}")

    print(f"\n{results['strategy1_name']}:")
    print(f"  Wins: {results['strategy1_wins']} ({results['strategy1_win_rate']:.1f}%)")
    print(f"  Average Score: {results['strategy1_avg_score']:.1f}")

    print(f"\n{results['strategy2_name']}:")
    print(f"  Wins: {results['strategy2_wins']} ({results['strategy2_win_rate']:.1f}%)")
    print(f"  Average Score: {results['strategy2_avg_score']:.1f}")

    print("\nSample Game Results:")
    for game in results["detailed_results"][:5]:  # Show first 5 games
        print(f"\nGame {game['game_number']}:")
        print(f"  Winner: {game['winner']}")
        print(f"  {results['strategy1_name']} Score: {game['strategy1_score']}")
        print(f"  {results['strategy2_name']} Score: {game['strategy2_score']}")
        print(f"  Margin: {game['margin']}")
        print(f"  Turns: {game['turns']}")


def main():
    parser = argparse.ArgumentParser(description="Run a battle between two Dominion strategies")
    parser.add_argument("strategy1", help="Name of first strategy")
    parser.add_argument("strategy2", help="Name of second strategy")
    parser.add_argument("--games", type=int, default=100, help="Number of games to play")
    args = parser.parse_args()

    # Default kingdom cards - could be made configurable
    kingdom_cards = [
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

    battle = StrategyBattle(kingdom_cards)
    results = battle.run_battle(args.strategy1, args.strategy2, args.games)
    print_results(results)


if __name__ == "__main__":
    main()
