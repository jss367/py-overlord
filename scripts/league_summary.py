"""Aggregate league runs across seeds into a per-arm table with spread.

A single seeded run is exactly reproducible but says nothing about how much
of its result is trajectory luck. On Oslo, fixing a name collision in the
opponent pool — a bookkeeping change that alters no strategy logic — moved the
gate by 14 percentage points, which is the scale of trajectory sensitivity
this pipeline has. Comparisons therefore need several seeds per arm, and a
difference smaller than the across-seed spread is not a result.

Usage::

    PYTHONPATH=. python scripts/league_summary.py reports/league/sweep_*.json

Runs are grouped by their ``arm`` field, so league and control reports can be
passed together.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from scipy import stats


def load_runs(paths: list[Path]) -> dict[str, dict[str, list[tuple[int, float]]]]:
    """Return ``{arm: {opponent: [(seed, win_rate), ...]}}``."""

    grouped: dict[str, dict[str, list[tuple[int, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        arm = payload.get("arm", "league")
        seed = payload.get("seed")
        for gate in payload.get("gate", []):
            grouped[arm][gate["opponent"]].append((seed, gate["win_rate"]))
    return grouped


def _spread(values: list[float]) -> tuple[float, float, float, float]:
    """Return (mean, stdev, min, max); stdev is 0 for a single value."""

    mean = statistics.fmean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, stdev, min(values), max(values)


def welch(a: list[float], b: list[float]) -> tuple[float, float]:
    """Welch's t statistic and two-sided p-value for two small samples.

    Welch rather than Student because the arms are not assumed to have equal
    trajectory variance — on Oslo the league arm's across-seed spread is
    several times the control's — and the samples are tiny.

    The p-value matters more than the t here: at four seeds per arm, |t| = 2
    is p = 0.11, not significance. Reporting the statistic alone invites
    exactly that misreading.
    """

    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan")
    result = stats.ttest_ind(b, a, equal_var=False)
    return float(result.statistic), float(result.pvalue)


def render(grouped: dict[str, dict[str, list[tuple[int, float]]]]) -> str:
    lines: list[str] = []
    opponents: list[str] = []
    for arm_data in grouped.values():
        for opponent in arm_data:
            if opponent not in opponents:
                opponents.append(opponent)

    for arm in sorted(grouped):
        lines.append(f"## {arm} arm")
        lines.append("")
        lines.append("| Opponent | Seeds | Mean | Stdev | Min | Max |")
        lines.append("|---|---|---|---|---|---|")
        for opponent in opponents:
            runs = grouped[arm].get(opponent, [])
            if not runs:
                continue
            values = [rate for _, rate in runs]
            mean, stdev, low, high = _spread(values)
            lines.append(
                f"| {opponent} | {len(values)} | {mean:.1f}% | {stdev:.1f} | "
                f"{low:.1f}% | {high:.1f}% |"
            )
        lines.append("")

    if "league" in grouped and "control" in grouped:
        lines.append("## League minus control")
        lines.append("")
        lines.append("| Opponent | Delta | Welch t | p | Verdict |")
        lines.append("|---|---|---|---|---|")
        for opponent in opponents:
            ctrl = [r for _, r in grouped["control"].get(opponent, [])]
            lg = [r for _, r in grouped["league"].get(opponent, [])]
            if not ctrl or not lg:
                continue
            delta = statistics.fmean(lg) - statistics.fmean(ctrl)
            t, pvalue = welch(ctrl, lg)
            # A non-significant result at this many seeds means "these runs
            # cannot resolve it", not "there is no effect" — the sweep is far
            # too small to support the second claim.
            if math.isnan(t):
                verdict = "need >=2 seeds per arm"
            elif pvalue < 0.05:
                verdict = "league better" if delta > 0 else "league worse"
            else:
                verdict = "unresolved at this seed count"
            t_text = "n/a" if math.isnan(t) else f"{t:+.2f}"
            p_text = "n/a" if math.isnan(pvalue) else f"{pvalue:.3f}"
            lines.append(
                f"| {opponent} | {delta:+.1f}pp | {t_text} | {p_text} | {verdict} |"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("reports", type=Path, nargs="+", help="league run JSON reports")
    parser.add_argument("--output", type=Path, default=None, help="write markdown here")
    args = parser.parse_args()

    grouped = load_runs(args.reports)
    if not grouped:
        raise SystemExit("No gate results found in the given reports")

    markdown = render(grouped)
    print(markdown)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
