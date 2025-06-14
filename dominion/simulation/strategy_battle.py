import argparse
from pathlib import Path
from typing import Any, Optional

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.simulation.game_logger import GameLogger
from dominion.strategy.strategy_loader import StrategyLoader


class StrategyBattle:
    """System for running battles between strategies."""

    def __init__(self, kingdom_cards: list[str], log_folder: str = "battle_logs"):
        self.kingdom_cards = kingdom_cards
        self.logger = GameLogger(log_folder=log_folder)
        self.strategy_loader = StrategyLoader()  # Now automatically loads all strategies

    def run_battle(self, strategy1_name: str, strategy2_name: str, num_games: int = 100) -> dict[str, Any]:
        """Run multiple games between two strategies"""
        # Get strategies from loader
        strategy1 = self.strategy_loader.get_strategy(strategy1_name)
        strategy2 = self.strategy_loader.get_strategy(strategy2_name)

        if not strategy1 or not strategy2:
            raise ValueError(f"Could not find strategies: {strategy1_name} and/or {strategy2_name}")

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

            # Create fresh AIs for each game using new strategy instances
            ai1 = GeneticAI(self.strategy_loader.get_strategy(strategy1_name))
            ai2 = GeneticAI(self.strategy_loader.get_strategy(strategy2_name))

            # Alternate who goes first
            if game_num % 2 == 0:
                winner, scores, log_path = self._run_game(ai1, ai2)
            else:
                winner, scores, log_path = self._run_game(ai2, ai1)

            # Record results
            game_result = {
                "game_number": game_num + 1,
                "winner": strategy1_name if winner == ai1 else strategy2_name,
                "strategy1_score": scores[ai1.name],
                "strategy2_score": scores[ai2.name],
                "margin": abs(scores[ai1.name] - scores[ai2.name]),
                "turns": self.logger.current_metrics.turn_count,
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

    def _run_game(self, ai1: GeneticAI, ai2: GeneticAI) -> tuple[GeneticAI, dict[str, int], Optional[str]]:
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

        # End game logging and capture log path if any
        log_path = self.logger.end_game(winner.name, scores, game_state.supply)

        return winner, scores, log_path


def main():
    parser = argparse.ArgumentParser(description="Run a battle between two Dominion strategies")
    parser.add_argument("strategy1_name", help="Name of first strategy")
    parser.add_argument("strategy2_name", help="Name of second strategy")
    parser.add_argument("--games", type=int, default=100, help="Number of games to play")
    args = parser.parse_args()

    # Default kingdom cards
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

    print(f"\nInitializing battle between {args.strategy1_name} and {args.strategy2_name}...")

    battle = StrategyBattle(kingdom_cards)

    # Print available strategies
    print("\nAvailable strategies:", ", ".join(battle.strategy_loader.list_strategies()))

    print(f"\nRunning {args.games} games...")
    results = battle.run_battle(args.strategy1_name, args.strategy2_name, args.games)

    if results:
        print_results(results)
    else:
        print("\nError: No results generated from battle")


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

    print("\nDetailed game results:")
    for game in results["detailed_results"]:
        print(f"\nGame {game['game_number']}:")
        print(f"  Winner: {game['winner']}")
        print(
            f"  Scores: {results['strategy1_name']}={game['strategy1_score']}, "
            f"{results['strategy2_name']}={game['strategy2_score']}"
        )
        print(f"  Margin: {game['margin']}")
        print(f"  Turns: {game['turns']}")
        if game.get("log_path"):
            print(f"  Log: {game['log_path']}")


if __name__ == "__main__":
    main()
