"""Run all registered strategies against each other and produce a leaderboard."""

from itertools import combinations
from pathlib import Path
from typing import Any, Dict

from dominion.simulation.strategy_battle import StrategyBattle


def run_full_battle(
    num_games: int = 10, use_shelters: bool = False
) -> Dict[str, Dict[str, Any]]:
    """Play each strategy against all others.

    Returns aggregated results keyed by strategy name.
    """
    battle = StrategyBattle(use_shelters=use_shelters)

    strategy_names = battle.strategy_loader.list_strategies()
    aggregated: Dict[str, Dict[str, Any]] = {
        name: {"wins": 0, "losses": 0, "games": 0} for name in strategy_names
    }

    for strat1, strat2 in combinations(strategy_names, 2):
        results = battle.run_battle(strat1, strat2, num_games)

        aggregated[strat1]["wins"] += results["strategy1_wins"]
        aggregated[strat1]["losses"] += results["strategy2_wins"]
        aggregated[strat1]["games"] += num_games

        aggregated[strat2]["wins"] += results["strategy2_wins"]
        aggregated[strat2]["losses"] += results["strategy1_wins"]
        aggregated[strat2]["games"] += num_games

    # Calculate win rates
    for stats in aggregated.values():
        if stats["games"]:
            stats["win_rate"] = stats["wins"] / stats["games"] * 100
        else:
            stats["win_rate"] = 0.0

    return aggregated


def generate_leaderboard_report(
    results: Dict[str, Dict[str, Any]], output_path: Path
) -> None:
    """Write a simple markdown leaderboard sorted by win rate."""
    lines = [
        "# Strategy Leaderboard",
        "",
        "| Strategy | Wins | Losses | Win Rate |",
        "| --- | --- | --- | --- |",
    ]
    for name, stats in sorted(
        results.items(), key=lambda i: i[1]["win_rate"], reverse=True
    ):
        lines.append(
            f"| {name} | {stats['wins']} | {stats['losses']} | {stats['win_rate']:.1f}% |"
        )
    output_path.write_text("\n".join(lines))
    print(f"Leaderboard written to {output_path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run all strategies against each other"
    )
    parser.add_argument("--games", type=int, default=10, help="Games per pairing")
    parser.add_argument(
        "--use-shelters", action="store_true", help="Start games with Shelters"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("leaderboard.md"),
        help="Output markdown file",
    )
    args = parser.parse_args()

    results = run_full_battle(num_games=args.games, use_shelters=args.use_shelters)
    generate_leaderboard_report(results, args.output)


if __name__ == "__main__":
    main()
