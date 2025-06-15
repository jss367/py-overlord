"""Compare Chapel Witch and Collection Patrician Rebuild strategies and produce an HTML report."""

from pathlib import Path

from dominion.reporting.html_report import generate_html_report
from dominion.simulation.strategy_battle import StrategyBattle


def main():
    # Kingdom includes cards required by both strategies
    kingdom_cards = [
        "Collection",
        "Patrician",
        "Rebuild",
        "Modify",
        "Forager",
        "Skulk",
        "Chapel",
        "Witch",
        "Village",
        "Market",
    ]

    battle = StrategyBattle(kingdom_cards)

    # Log every game so detailed logs are saved
    battle.logger.log_frequency = 1

    results = battle.run_battle(
        "Chapel Witch", "Collection Patrician Rebuild", num_games=100
    )

    generate_html_report(results, Path("reports/chapel_vs_collection_report.html"))


if __name__ == "__main__":
    main()
