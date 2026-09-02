import math

import pytest

from dominion.analysis.seed_stats import paired_t, spread, t_interval, welch


def test_spread_single_and_multiple():
    assert spread([40.0]) == (40.0, 0.0, 40.0, 40.0)
    mean, stdev, low, high = spread([40.0, 50.0, 60.0])
    assert mean == 50.0 and stdev == pytest.approx(10.0) and (low, high) == (40.0, 60.0)
    with pytest.raises(ValueError):
        spread([])


def test_t_interval_contains_mean_and_widens_with_fewer_samples():
    assert t_interval([42.0]) == (42.0, 42.0)
    assert t_interval([50.0, 50.0, 50.0]) == (50.0, 50.0)
    lo3, hi3 = t_interval([40.0, 50.0, 60.0])
    assert lo3 < 50.0 < hi3
    assert hi3 - lo3 == pytest.approx(2 * 4.302653 * 10.0 / math.sqrt(3), rel=1e-4)
    lo5, hi5 = t_interval([40.0, 45.0, 50.0, 55.0, 60.0])
    assert hi5 - lo5 < hi3 - lo3


def test_welch_needs_two_per_arm_and_separates_clear_effects():
    t, p = welch([1.0], [2.0, 3.0])
    assert math.isnan(t) and math.isnan(p)
    t, p = welch([40.0, 41.0, 39.0, 40.5], [60.0, 61.0, 59.0, 60.5])
    assert t > 0 and p < 0.001
    _, p_same = welch([40.0, 50.0, 60.0], [41.0, 49.0, 61.0])
    assert p_same > 0.5


def test_paired_t_uses_matched_pairs():
    with pytest.raises(ValueError):
        paired_t([1.0, 2.0], [1.0])
    assert all(math.isnan(v) for v in paired_t([1.0], [2.0]))
    assert all(math.isnan(v) for v in paired_t([1.0, 2.0], [3.0, 4.0]))  # identical diffs
    # Large between-board spread, consistent small improvement: paired resolves it.
    base = [10.0, 30.0, 50.0, 70.0, 90.0]
    cand = [x - 2.0 + d for x, d in zip(base, [0.1, -0.1, 0.05, -0.05, 0.0])]
    _, p = paired_t(base, cand)
    assert p < 0.01
