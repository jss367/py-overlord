import argparse
from pathlib import Path
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.reporting.html_report import generate_html_report

# Custom kingdom used for Custom Board vs Custom Board2
CUSTOM_KINGDOM = [
    "Collection",
    "Emporium",
    "Forager",
    "Miser",
    "Modify",
    "Patrician",
    "Rats",
    "Rebuild",
    "Skulk",
    "Snowy Village",
]

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare the two custom board strategies"
    )
    parser.add_argument("--games", type=int, default=10, help="Number of games to play")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/custom_board_vs_custom_board2_report.html"),
        help="Output HTML file",
    )
    args = parser.parse_args()

    battle = StrategyBattle(kingdom_cards=CUSTOM_KINGDOM)
    battle.logger.log_frequency = 1

    results = battle.run_battle("Custom Board Strategy", "Custom Board Strategy2", args.games)
    generate_html_report(results, args.output)
    print("Battle results:")
    for key, value in results.items():
        if key != "detailed_results":
            print(f"{key}: {value}")

if __name__ == "__main__":
    main()
