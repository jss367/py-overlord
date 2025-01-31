import json
import argparse
from dominion.simulation.game_runner import GameRunner
from dominion.ai.genetic_ai import GeneticAI
from dominion.strategies.strategy import Strategy
from dominion.simulation.game_logger import GameLogger


def load_strategy_from_file(filepath: str) -> Strategy:
    """Load a strategy from a JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)

    strategy = Strategy()

    # Load gain and play priorities
    if "priorities" in data:
        if "gain" in data["priorities"]:
            strategy.gain_priorities = data["priorities"]["gain"]
        if "play" in data["priorities"]:
            strategy.play_priorities = data["priorities"]["play"]

    # Load weights
    if "weights" in data:
        weights = data["weights"]
        strategy.action_weight = weights.get("action", 0.5)
        strategy.treasure_weight = weights.get("treasure", 0.5)
        strategy.victory_weight = (
            weights.get("victory", 0.5)
            if isinstance(weights.get("victory"), float)
            else 0.5
        )
        strategy.engine_weight = weights.get("engine", 0.5)

    return strategy


def run_strategy_battle(
    strategy1_path: str,
    strategy2_path: str,
    num_games: int = 100,
    kingdom_cards: list[str] = None,
) -> dict:
    """Run multiple games between two strategies and return statistics."""

    # Default kingdom cards if none provided
    if kingdom_cards is None:
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

    # Load strategies
    strategy1 = load_strategy_from_file(strategy1_path)
    strategy2 = load_strategy_from_file(strategy2_path)

    # Create AIs
    ai1 = GeneticAI(strategy1)
    ai2 = GeneticAI(strategy2)

    # Set up game runner with logger
    logger = GameLogger(log_folder="battle_logs")
    game_runner = GameRunner(kingdom_cards, logger=logger)

    # Track results
    results = {
        "strategy1_wins": 0,
        "strategy2_wins": 0,
        "strategy1_total_score": 0,
        "strategy2_total_score": 0,
        "games_played": num_games,
        "detailed_results": [],
    }

    # Run games
    print(f"\nRunning {num_games} games between strategies...")
    print(f"Strategy 1: {strategy1_path}")
    print(f"Strategy 2: {strategy2_path}\n")

    for game_num in range(num_games):
        print(f"Playing game {game_num + 1}/{num_games}...")

        # Alternate who goes first
        if game_num % 2 == 0:
            winner, scores = game_runner.run_game(ai1, ai2)
        else:
            winner, scores = game_runner.run_game(ai2, ai1)

        # Record results
        game_result = {
            "game_number": game_num + 1,
            "winner": "strategy1" if winner == ai1 else "strategy2",
            "strategy1_score": scores[ai1.name],
            "strategy2_score": scores[ai2.name],
            "margin": abs(scores[ai1.name] - scores[ai2.name]),
        }
        results["detailed_results"].append(game_result)

        if winner == ai1:
            results["strategy1_wins"] += 1
        else:
            results["strategy2_wins"] += 1

        results["strategy1_total_score"] += scores[ai1.name]
        results["strategy2_total_score"] += scores[ai2.name]

    # Calculate averages
    results["strategy1_win_rate"] = results["strategy1_wins"] / num_games * 100
    results["strategy2_win_rate"] = results["strategy2_wins"] / num_games * 100
    results["strategy1_avg_score"] = results["strategy1_total_score"] / num_games
    results["strategy2_avg_score"] = results["strategy2_total_score"] / num_games

    return results


def print_results(results: dict):
    """Print battle results in a readable format."""
    print("\n=== Strategy Battle Results ===")
    print(f"\nGames played: {results['games_played']}")
    print("\nStrategy 1:")
    print(f"  Wins: {results['strategy1_wins']} ({results['strategy1_win_rate']:.1f}%)")
    print(f"  Average Score: {results['strategy1_avg_score']:.1f}")
    print("\nStrategy 2:")
    print(f"  Wins: {results['strategy2_wins']} ({results['strategy2_win_rate']:.1f}%)")
    print(f"  Average Score: {results['strategy2_avg_score']:.1f}")

    # Print some detailed game results
    print("\nSample Game Results:")
    for game in results["detailed_results"][:5]:  # Show first 5 games
        print(f"\nGame {game['game_number']}:")
        print(f"  Winner: Strategy {game['winner'][-1]}")
        print(f"  Strategy 1 Score: {game['strategy1_score']}")
        print(f"  Strategy 2 Score: {game['strategy2_score']}")
        print(f"  Margin: {game['margin']}")


def main():
    parser = argparse.ArgumentParser(
        description="Run a battle between two Dominion strategies."
    )
    parser.add_argument("strategy1", help="Path to first strategy JSON file")
    parser.add_argument("strategy2", help="Path to second strategy JSON file")
    parser.add_argument(
        "--games", type=int, default=100, help="Number of games to play"
    )
    args = parser.parse_args()

    results = run_strategy_battle(args.strategy1, args.strategy2, args.games)
    print_results(results)


if __name__ == "__main__":
    main()
