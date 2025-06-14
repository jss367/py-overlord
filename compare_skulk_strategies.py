"""Run Skulk Rebuild strategies and produce an HTML report."""

from pathlib import Path

from dominion.reporting.html_report import generate_html_report
from dominion.simulation.strategy_battle import StrategyBattle


def main():
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

    # Reduce logging to keep console output clean
    battle.logger.log_frequency = 1000

    results = battle.run_battle(
        "Skulk Rebuild", "Skulk Rebuild Improved", num_games=100
    )

    generate_html_report(results, Path("skulk_report.html"))


if __name__ == "__main__":
    main()

