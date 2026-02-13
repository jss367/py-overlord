"""Generate a leaderboard for a given board.

Automatically discovers all compatible strategies (from generated_strategies/
and dominion/strategy/strategies/), runs a round-robin tournament, and
produces an HTML report.

A strategy is compatible with a board if every kingdom card it references
is either a base supply card (Copper, Silver, Gold, Estate, Duchy, Province,
Curse) or present in the board's kingdom.

Usage:
    python leaderboard.py --board boards/siege_engine.txt
    python leaderboard.py --board boards/siege_engine.txt --games 1000
"""

import argparse
import importlib
import logging
import sys
from datetime import datetime
from pathlib import Path

import coloredlogs

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.reporting.html_report import generate_leaderboard_html
from dominion.simulation.strategy_battle import StrategyBattle

logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger)

BASE_SUPPLY = {
    "Copper", "Silver", "Gold",
    "Estate", "Duchy", "Province",
    "Curse",
}


def _find_factory(module):
    """Find the create_* factory function in a module."""
    for name in dir(module):
        if name.startswith("create_") and callable(getattr(module, name)):
            return name, getattr(module, name)
    return None, None


def _get_kingdom_refs(strategy) -> set[str]:
    """Extract all card names referenced in a strategy's priority lists."""
    names = set()
    for list_name in ("gain_priority", "action_priority", "treasure_priority", "trash_priority"):
        for rule in getattr(strategy, list_name, []):
            names.add(rule.card_name)
    return names


def _is_compatible(factory, board_kingdom: set[str]) -> bool:
    """Check if a strategy only references cards available on the board."""
    try:
        strategy = factory()
        refs = _get_kingdom_refs(strategy)
        non_base = refs - BASE_SUPPLY
        if not non_base:
            return True  # Only references base supply (e.g. Big Money)
        return non_base.issubset(board_kingdom)
    except Exception:
        return False


def discover_strategies(board_kingdom: set[str]) -> dict[str, callable]:
    """Discover all compatible strategies from known locations."""
    strategies = {}

    # Search dominion/strategy/strategies/
    strat_dir = Path("dominion/strategy/strategies")
    for py_file in sorted(strat_dir.glob("*.py")):
        if py_file.name.startswith("_") or py_file.name == "base_strategy.py":
            continue
        module_path = py_file.with_suffix("").as_posix().replace("/", ".")
        try:
            mod = importlib.import_module(module_path)
            func_name, factory = _find_factory(mod)
            if factory is None:
                continue
            if _is_compatible(factory, board_kingdom):
                # Use a readable name from the class
                strat = factory()
                name = getattr(strat, "name", func_name)
                strategies[name] = factory
                logger.info("  Found: %s (%s)", name, py_file.name)
            else:
                logger.debug("  Skipped (incompatible): %s", py_file.name)
        except Exception as e:
            logger.debug("  Skipped (error): %s — %s", py_file.name, e)

    # Search generated_strategies/
    gen_dir = Path("generated_strategies")
    if gen_dir.exists():
        for py_file in sorted(gen_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_path = py_file.with_suffix("").as_posix().replace("/", ".")
            try:
                mod = importlib.import_module(module_path)
                func_name, factory = _find_factory(mod)
                if factory is None:
                    continue
                if _is_compatible(factory, board_kingdom):
                    strat = factory()
                    name = getattr(strat, "name", func_name)
                    # Use filename if the name looks auto-generated
                    if name.startswith("gen") and "-" in name:
                        name = py_file.stem
                    # Deduplicate names
                    if name in strategies:
                        name = f"{name} ({py_file.stem})"
                    strategies[name] = factory
                    logger.info("  Found: %s (%s)", name, py_file.name)
                else:
                    logger.debug("  Skipped (incompatible): %s", py_file.name)
            except Exception as e:
                logger.debug("  Skipped (error): %s — %s", py_file.name, e)

    return strategies


def round_robin(strategies, battle, num_games):
    """Run a round-robin tournament, return {name: {wins, losses, win_rate}}."""
    names = list(strategies.keys())
    results = {n: {"wins": 0, "losses": 0} for n in names}
    total = len(names) * (len(names) - 1) // 2
    done = 0

    kingdom = battle.board_config.kingdom_cards if battle.board_config else None

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            na, nb = names[i], names[j]
            done += 1
            logger.info("[%d/%d] %s vs %s (%d games)...", done, total, na, nb, num_games)
            a_wins = 0
            for g in range(num_games):
                ai_a = GeneticAI(strategies[na]())
                ai_b = GeneticAI(strategies[nb]())
                if g % 2 == 0:
                    winner, _, _, _ = battle.run_game(ai_a, ai_b, kingdom)
                else:
                    winner, _, _, _ = battle.run_game(ai_b, ai_a, kingdom)
                if winner == ai_a:
                    a_wins += 1
            b_wins = num_games - a_wins
            results[na]["wins"] += a_wins
            results[na]["losses"] += b_wins
            results[nb]["wins"] += b_wins
            results[nb]["losses"] += a_wins
            logger.info(
                "  %s: %d (%.1f%%) | %s: %d (%.1f%%)",
                na, a_wins, a_wins / num_games * 100,
                nb, b_wins, b_wins / num_games * 100,
            )

    for name, stats in results.items():
        total_games = stats["wins"] + stats["losses"]
        stats["win_rate"] = stats["wins"] / total_games * 100 if total_games else 0

    return results


def main():
    parser = argparse.ArgumentParser(description="Generate a leaderboard for a board")
    parser.add_argument(
        "--board", required=True,
        help="Board definition file (e.g. boards/siege_engine.txt)",
    )
    parser.add_argument(
        "--games", type=int, default=50,
        help="Games per pair of strategies (default: 50)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output HTML file (default: auto-generated in reports/)",
    )
    args = parser.parse_args()

    board_config = load_board(args.board)
    board_name = Path(args.board).stem
    board_kingdom = set(board_config.kingdom_cards)

    logger.info("Board: %s", args.board)
    logger.info("Kingdom: %s", ", ".join(sorted(board_kingdom)))
    logger.info("")
    logger.info("Discovering compatible strategies...")

    strategies = discover_strategies(board_kingdom)

    if len(strategies) < 2:
        logger.error("Need at least 2 compatible strategies, found %d", len(strategies))
        sys.exit(1)

    logger.info("")
    logger.info("Found %d compatible strategies", len(strategies))
    logger.info("")

    battle = StrategyBattle(board_config=board_config, log_frequency=0)
    results = round_robin(strategies, battle, args.games)

    # Enrich results with description and kingdom cards used
    for name, factory in strategies.items():
        strat = factory()
        refs = _get_kingdom_refs(strat) - BASE_SUPPLY
        results[name]["description"] = getattr(strat, "description", "")
        results[name]["cards"] = sorted(refs)

    logger.info("")
    logger.info("Leaderboard:")
    ranked = sorted(results.items(), key=lambda x: x[1]["win_rate"], reverse=True)
    for rank, (name, stats) in enumerate(ranked, 1):
        logger.info(
            "  #%d %s: %d-%d (%.1f%%)",
            rank, name, stats["wins"], stats["losses"], stats["win_rate"],
        )

    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path("reports") / f"{board_name}_leaderboard_{timestamp}.html"
    else:
        output_path = args.output

    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_leaderboard_html(results, output_path, verbose=True)
    logger.info("Report: %s", output_path)


if __name__ == "__main__":
    main()
