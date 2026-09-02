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

Evolve mode is seeded (``--seed-base``, default 1), so a run is reproducible.
One trajectory says nothing about how much of its gap is luck, though: pass
``--seeds N`` to evolve each board N times (seeds base..base+N-1) and get a
Student-t interval over seeds plus a gap on the across-seed mean. To judge a
pipeline change, run the same budget before and after and pass the earlier
JSON as ``--baseline``: the report then adds a per-board Welch test and a
paired test on the suite mean gap (see scripts/calibration_summary.py to do
this on saved reports).

    PYTHONPATH=. python scripts/calibration_suite.py --mode evolve --seeds 4 \
        --baseline reports/calibration/evolve.json --output-dir reports/calibration/new
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
    load_outcomes_json,
    render_comparison,
    render_evolve_report,
    render_sanity_report,
    run_sanity,
    save_outcomes_json,
)

logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid int value: {value!r}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value!r}")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["sanity", "evolve"], default="sanity")
    parser.add_argument(
        "--games",
        type=positive_int,
        default=400,
        help="Games per matchup (sanity battles and evolve-mode confirmation)",
    )
    parser.add_argument(
        "--boards",
        type=str,
        default=None,
        help=f"Comma-separated board keys (default: all). Known: {', '.join(e.key for e in CALIBRATION_SUITE)}",
    )
    parser.add_argument("--population", type=positive_int, default=40)
    parser.add_argument("--generations", type=positive_int, default=40)
    parser.add_argument("--games-per-eval", type=positive_int, default=20)
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Worker processes for playing games (0 = one per CPU, 1 = run in-process)",
    )
    parser.add_argument(
        "--seeds",
        type=positive_int,
        default=1,
        help="Evolve mode: independent seeded runs per board (default: 1)",
    )
    parser.add_argument(
        "--seed-base",
        type=int,
        default=1,
        help="Evolve mode: first seed; run k uses seed-base + k (default: 1)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Evolve mode: earlier evolve JSON to compare against (per-board Welch test)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("reports/calibration")
    )
    args = parser.parse_args()

    boards = [key.strip() for key in args.boards.split(",") if key.strip()] if args.boards else None
    entries = entries_for_keys(boards)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "sanity":
        outcomes = run_sanity(entries, args.games, workers=args.workers)
        report = render_sanity_report(outcomes)
        report_path = args.output_dir / "sanity.md"
        json_path = args.output_dir / "sanity.json"
    else:
        outcomes = []
        seeds = [args.seed_base + k for k in range(args.seeds)]
        json_path = args.output_dir / "evolve.json"
        for entry in entries:
            for seed in seeds:
                logger.info("Evolving champion for board %s (seed %d) ...", entry.key, seed)
                outcome, _meta, champion = evolve_and_evaluate(
                    entry,
                    confirm_games=args.games,
                    seed=seed,
                    population_size=args.population,
                    generations=args.generations,
                    games_per_eval=args.games_per_eval,
                    workers=args.workers,
                )
                logger.info(
                    "%s seed %d: champion won %.1f%% of %d games vs %s",
                    entry.key,
                    seed,
                    outcome.winrate_a,
                    outcome.games,
                    entry.known_best,
                )
                outcomes.append(outcome)
                # Checkpoint after every run so a long sweep that dies part-way
                # still leaves a readable, comparable JSON behind.
                save_outcomes_json(outcomes, json_path)
                suffix = f"_seed{seed}" if args.seeds > 1 else ""
                champion_path = args.output_dir / f"champion_{entry.key}{suffix}.py"
                class_suffix = f"Seed{seed}" if args.seeds > 1 else ""
                save_strategy_as_python(
                    champion,
                    champion_path,
                    class_name=f"Champion{entry.key.title().replace('_', '')}{class_suffix}",
                )
                logger.info("Champion genome saved to %s", champion_path)
        report = render_evolve_report(outcomes)
        if args.baseline is not None:
            comparison = render_comparison(
                load_outcomes_json(args.baseline),
                outcomes,
                baseline_label=args.baseline.stem,
                candidate_label="this run",
            )
            report = report + "\n" + comparison
        report_path = args.output_dir / "evolve.md"

    report_path.write_text(report, encoding="utf-8")
    save_outcomes_json(outcomes, json_path)
    print(report)
    print(f"Report written to {report_path} (JSON: {json_path})")


if __name__ == "__main__":
    main()
