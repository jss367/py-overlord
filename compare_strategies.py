"""Run two strategies and generate an HTML report."""

from pathlib import Path
import argparse

from dominion.boards.loader import load_board
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
    parser.add_argument("--board", help="Board definition file to enforce kingdom and landscapes")

    args = parser.parse_args()

    board_config = None
    if args.board:
        board_config = load_board(args.board)

    battle = StrategyBattle(use_shelters=args.use_shelters, board_config=board_config)
    battle.logger.log_frequency = 1

    results = battle.run_battle(args.strategy1, args.strategy2, args.games)
    generate_html_report(results, args.output)


if __name__ == "__main__":
    main()
