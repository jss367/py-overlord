"""Run two strategies and generate an HTML report."""

from pathlib import Path
import argparse

from dominion.simulation.strategy_battle import StrategyBattle
from dominion.reporting.html_report import generate_html_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two strategies and produce an HTML report"
    )
    parser.add_argument("strategy1", help="First strategy name")
    parser.add_argument("strategy2", help="Second strategy name")
    parser.add_argument("--games", type=int, default=100, help="Number of games to play")
    parser.add_argument(
        "--use-shelters",
        action="store_true",
        help="Start games with Shelters instead of Estates",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/strategy_report.html"),
        help="Output HTML file",
    )
    args = parser.parse_args()

    battle = StrategyBattle(use_shelters=args.use_shelters)
    battle.logger.log_frequency = 1

    results = battle.run_battle(args.strategy1, args.strategy2, args.games)
    generate_html_report(results, args.output)


if __name__ == "__main__":
    main()
