"""Summarize or compare saved calibration evolve reports.

The evolve JSON written by ``scripts/calibration_suite.py`` holds one record
per (board, seed). This script re-renders the across-seed table for one
report and, given ``--baseline``, adds a per-board Welch test plus a paired
test on the suite mean gap — the comparison any claim about a pipeline
change has to clear. Old single-seed reports load fine; they simply cannot
resolve a per-board test and the verdict says so.

    PYTHONPATH=. python scripts/calibration_summary.py reports/calibration/new/evolve.json \\
        --baseline reports/calibration/evolve.json --output reports/calibration/new/compare.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dominion.analysis.calibration import (
    load_outcomes_json,
    render_comparison,
    render_evolve_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("report", type=Path, help="evolve JSON to summarize")
    parser.add_argument("--baseline", type=Path, default=None, help="earlier evolve JSON to compare against")
    parser.add_argument("--output", type=Path, default=None, help="write markdown here")
    args = parser.parse_args()

    candidate = load_outcomes_json(args.report)
    if not candidate:
        raise SystemExit(f"No outcomes in {args.report}")
    markdown = render_evolve_report(candidate)
    if args.baseline is not None:
        markdown += "\n" + render_comparison(
            load_outcomes_json(args.baseline),
            candidate,
            baseline_label=args.baseline.stem if args.baseline.stem != args.report.stem else "baseline",
            candidate_label=args.report.stem if args.baseline.stem != args.report.stem else "candidate",
        )
    print(markdown)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
