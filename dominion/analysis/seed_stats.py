"""Small-sample statistics for across-seed comparisons.

A seeded run of this pipeline is exactly reproducible but wildly
trajectory-sensitive: a bookkeeping change that alters no strategy logic
has moved a gate by 14 percentage points at a fixed seed. Any claim about a
mechanism therefore needs several seeds per arm, and the spread across those
seeds is part of the result. These helpers are shared by the calibration
suite and the league summary so both report the same intervals and tests.
"""

from __future__ import annotations

import math
import statistics
from typing import Sequence

from scipy import stats


def spread(values: Sequence[float]) -> tuple[float, float, float, float]:
    """Return ``(mean, stdev, min, max)``; stdev is 0 for a single value."""

    values = list(values)
    if not values:
        raise ValueError("spread() needs at least one value")
    mean = statistics.fmean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, stdev, min(values), max(values)


def t_interval(values: Sequence[float], confidence: float = 0.95) -> tuple[float, float]:
    """Student-t confidence interval for the mean of a small sample.

    With one value there is no spread to estimate, so the interval is the
    value itself; callers that have a per-run interval (e.g. a Wilson
    interval on one run's win rate) should prefer that in the n=1 case.
    """

    values = list(values)
    if not values:
        raise ValueError("t_interval() needs at least one value")
    mean = statistics.fmean(values)
    if len(values) < 2:
        return (mean, mean)
    stdev = statistics.stdev(values)
    if stdev == 0.0:
        return (mean, mean)
    half_width = stats.t.ppf(0.5 + confidence / 2, len(values) - 1) * stdev / math.sqrt(len(values))
    return (mean - half_width, mean + half_width)


def welch(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Welch's t statistic and two-sided p-value for ``b`` against ``a``.

    Welch rather than Student because the arms are not assumed to have equal
    trajectory variance — on Oslo the league arm's across-seed spread is
    several times the control's — and the samples are tiny.

    The p-value matters more than the t here: at four seeds per arm, |t| = 2
    is p = 0.11, not significance. Reporting the statistic alone invites
    exactly that misreading. Returns ``(nan, nan)`` when either side has
    fewer than two values.
    """

    a = list(a)
    b = list(b)
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan")
    result = stats.ttest_ind(b, a, equal_var=False)
    return float(result.statistic), float(result.pvalue)


def paired_t(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Paired t statistic and two-sided p-value for ``b - a`` over matched pairs.

    Used for suite-level comparisons where each board contributes one value
    per arm: pairing by board removes the between-board spread, which is
    much larger than the effect of a pipeline change. Returns ``(nan, nan)``
    with fewer than two pairs or when every difference is identical.
    """

    a = list(a)
    b = list(b)
    if len(a) != len(b):
        raise ValueError("paired_t() needs equally long sequences")
    if len(a) < 2:
        return float("nan"), float("nan")
    diffs = [y - x for x, y in zip(a, b)]
    if len(set(diffs)) == 1:
        return float("nan"), float("nan")
    result = stats.ttest_rel(b, a)
    return float(result.statistic), float(result.pvalue)
