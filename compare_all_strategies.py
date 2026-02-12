"""Run all registered strategies against each other and produce a leaderboard."""

from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Optional

from dominion.boards.loader import BoardConfig, load_board
from dominion.simulation.strategy_battle import BASIC_CARDS, StrategyBattle
from dominion.reporting.html_report import generate_leaderboard_html


def run_full_battle(
    num_games: int = 10,
    use_shelters: bool = False,
    board_config: Optional[BoardConfig] = None,
) -> Dict[str, Dict[str, Any]]:
    """Play each strategy against all others.

    Returns aggregated results keyed by strategy name.
    """
    battle = StrategyBattle(
        use_shelters=use_shelters,
        log_frequency=0,
        board_config=board_config,
    )

    strategy_names = battle.strategy_loader.list_strategies()

    # Collect metadata and optionally filter to board-compatible strategies
    board_cards: Optional[set[str]] = None
    if board_config:
        board_cards = set(board_config.kingdom_cards)

    compatible_names = []
    all_meta: Dict[str, Dict[str, Any]] = {}

    for name in strategy_names:
        strat = battle.strategy_loader.get_strategy(name)
        if not strat:
            continue
        cards = battle._extract_cards_from_strategy(strat)
        kingdom_cards = sorted(c for c in cards if c not in BASIC_CARDS)
        desc = getattr(strat, "description", "")

        if board_cards is not None:
            # Only include strategies whose cards are all on the board
            if not set(kingdom_cards).issubset(board_cards):
                print(f"  Excluding {name}: uses cards not on board ({', '.join(sorted(set(kingdom_cards) - board_cards))})")
                continue

        compatible_names.append(name)
        all_meta[name] = {
            "wins": 0, "losses": 0, "games": 0,
            "cards": kingdom_cards,
            "description": desc,
        }

    strategy_names = compatible_names
    aggregated = all_meta

    total_pairings = len(list(combinations(strategy_names, 2)))
    print(f"Running {total_pairings} pairings ({len(strategy_names)} strategies, {num_games} games each)...")

    for i, (strat1, strat2) in enumerate(combinations(strategy_names, 2), 1):
        if i % 10 == 0 or i == total_pairings:
            print(f"  Pairing {i}/{total_pairings}: {strat1} vs {strat2}")
        try:
            results = battle.run_battle(strat1, strat2, num_games)
        except Exception as exc:
            print(f"  Skipping {strat1} vs {strat2}: {exc}")
            continue

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
        "--board",
        help="Board definition file; only strategies compatible with this board are included",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML file (default: reports/leaderboard.html)",
    )
    args = parser.parse_args()

    board_config = load_board(args.board) if args.board else None

    results = run_full_battle(
        num_games=args.games,
        use_shelters=args.use_shelters,
        board_config=board_config,
    )

    if args.output:
        output = args.output
    elif args.board:
        board_name = Path(args.board).stem
        output = Path(f"reports/leaderboard_{board_name}.html")
    else:
        output = Path("reports/leaderboard_all.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_leaderboard_html(results, output)
    print(f"Leaderboard written to {output}")


if __name__ == "__main__":
    main()
