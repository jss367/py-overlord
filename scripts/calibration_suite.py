"""Run the ground-truth calibration suite.

Sanity mode (fast, run this first): battles each board's known-best strategy
against Big Money. Every board should PASS — a FAIL means the simulator or
the known-best encoding is broken on that board, and evolution results there
cannot be trusted.

    PYTHONPATH=. python scripts/calibration_suite.py --mode sanity --games 400

Evolve mode (slow): runs the genetic trainer on each board with its default
settings, then battles the champion against the known-best strategy. The gap
(percentage points of champion win rate below 50%) is the number this repo
is trying to drive to zero.

    PYTHONPATH=. python scripts/calibration_suite.py --mode evolve \
        --population 40 --generations 40 --games-per-eval 20 --games 400

Use --boards to restrict either mode to a comma-separated subset of keys.
"""

import argparse
import logging
from pathlib import Path

import coloredlogs

from dominion.runner import save_strategy_as_python

from dominion.analysis.calibration import (
    CALIBRATION_SUITE,
    entries_for_keys,
    evolve_and_evaluate,
    render_evolve_report,
    render_sanity_report,
    run_sanity,
    save_outcomes_json,
)

logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["sanity", "evolve"], default="sanity")
    parser.add_argument(
        "--games",
        type=int,
        default=400,
        help="Games per matchup (sanity battles and evolve-mode confirmation)",
    )
    parser.add_argument(
        "--boards",
        type=str,
        default=None,
        help=f"Comma-separated board keys (default: all). Known: {', '.join(e.key for e in CALIBRATION_SUITE)}",
    )
    parser.add_argument("--population", type=int, default=40)
    parser.add_argument("--generations", type=int, default=40)
    parser.add_argument("--games-per-eval", type=int, default=20)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("reports/calibration")
    )
    args = parser.parse_args()

    entries = entries_for_keys(args.boards.split(",") if args.boards else None)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "sanity":
        outcomes = run_sanity(entries, args.games)
        report = render_sanity_report(outcomes)
        report_path = args.output_dir / "sanity.md"
        json_path = args.output_dir / "sanity.json"
    else:
        outcomes = []
        for entry in entries:
            logger.info("Evolving champion for board %s ...", entry.key)
            outcome, _meta, champion = evolve_and_evaluate(
                entry,
                confirm_games=args.games,
                population_size=args.population,
                generations=args.generations,
                games_per_eval=args.games_per_eval,
            )
            logger.info(
                "%s: champion won %.1f%% of %d games vs %s",
                entry.key,
                outcome.winrate_a,
                outcome.games,
                entry.known_best,
            )
            outcomes.append(outcome)
            champion_path = args.output_dir / f"champion_{entry.key}.py"
            save_strategy_as_python(
                champion, champion_path, class_name=f"Champion{entry.key.title().replace('_', '')}"
            )
            logger.info("Champion genome saved to %s", champion_path)
        report = render_evolve_report(outcomes)
        report_path = args.output_dir / "evolve.md"
        json_path = args.output_dir / "evolve.json"

    report_path.write_text(report, encoding="utf-8")
    save_outcomes_json(outcomes, json_path)
    print(report)
    print(f"Report written to {report_path} (JSON: {json_path})")


if __name__ == "__main__":
    main()
