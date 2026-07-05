"""Tests for the ground-truth calibration suite.

The calibration suite pairs boards with community-known best strategies so
the evolution pipeline can be scored against an external reference instead
of only against itself.
"""

import pytest

from dominion.analysis.calibration import (
    CALIBRATION_SUITE,
    MatchOutcome,
    entries_for_keys,
    gap_points,
    render_evolve_report,
    render_sanity_report,
    wilson_interval,
)
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategy_loader import StrategyLoader

BASIC_SUPPLY = {
    "Copper",
    "Silver",
    "Gold",
    "Platinum",
    "Estate",
    "Duchy",
    "Province",
    "Colony",
    "Curse",
}


@pytest.fixture(scope="module")
def loader():
    return StrategyLoader()


def test_suite_is_nonempty_with_unique_keys():
    keys = [entry.key for entry in CALIBRATION_SUITE]
    assert len(keys) >= 8
    assert len(set(keys)) == len(keys)


def test_entries_for_keys_filters_and_rejects_unknown():
    all_entries = entries_for_keys(None)
    assert list(all_entries) == list(CALIBRATION_SUITE)

    first = CALIBRATION_SUITE[0]
    assert [e.key for e in entries_for_keys([first.key])] == [first.key]

    with pytest.raises(ValueError, match="no-such-board"):
        entries_for_keys(["no-such-board"])


@pytest.mark.parametrize("entry", CALIBRATION_SUITE, ids=lambda e: e.key)
def test_board_file_loads_and_all_cards_resolve(entry):
    config = load_board(entry.board_path())
    assert len(config.kingdom_cards) == 10
    for name in config.kingdom_cards:
        get_card(name)  # raises on unknown card


@pytest.mark.parametrize("entry", CALIBRATION_SUITE, ids=lambda e: e.key)
def test_known_best_strategy_loads_and_fits_board(entry, loader):
    strategy = loader.get_strategy(entry.known_best)
    assert strategy is not None, f"strategy {entry.known_best!r} not registered"

    config = load_board(entry.board_path())
    allowed = set(config.kingdom_cards) | BASIC_SUPPLY
    for rules in (
        strategy.gain_priority,
        strategy.action_priority,
        strategy.treasure_priority,
        strategy.trash_priority,
    ):
        for rule in rules:
            if isinstance(rule, PriorityRule):
                assert rule.card_name in allowed, (
                    f"{entry.known_best} references {rule.card_name!r}, "
                    f"which is not on board {entry.key}"
                )


def test_wilson_interval_midpoint():
    lo, hi = wilson_interval(50, 100)
    assert 0.40 < lo < 0.42
    assert 0.58 < hi < 0.60


def test_wilson_interval_extremes():
    lo, hi = wilson_interval(10, 10)
    assert lo > 0.65
    assert hi > 0.99

    lo, hi = wilson_interval(0, 10)
    assert lo < 0.01
    assert hi < 0.35

    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_gap_points():
    assert gap_points(50.0) == 0.0
    assert gap_points(62.0) == 0.0
    assert gap_points(43.5) == pytest.approx(6.5)


def _outcome(**overrides):
    base = dict(
        board="smithy_bm",
        strategy_a="Double Smithy",
        strategy_b="Big Money",
        wins_a=140,
        games=200,
    )
    base.update(overrides)
    return MatchOutcome(**base)


def test_match_outcome_winrate_and_ci():
    outcome = _outcome()
    assert outcome.winrate_a == pytest.approx(70.0)
    lo, hi = outcome.ci_a
    assert 60.0 < lo < 70.0 < hi < 80.0


def test_render_sanity_report_shows_boards_and_verdicts():
    strong = _outcome()
    weak = _outcome(board="rebuild_duchy", strategy_a="Rebuild Rush", wins_a=90)
    text = render_sanity_report([strong, weak])
    assert "smithy_bm" in text
    assert "Double Smithy" in text
    assert "70.0" in text
    assert "PASS" in text
    assert "FAIL" in text


def test_render_evolve_report_includes_mean_gap():
    tied = _outcome(strategy_a="Champion", strategy_b="Double Smithy", wins_a=100)
    behind = _outcome(
        board="rebuild_duchy",
        strategy_a="Champion",
        strategy_b="Rebuild Rush",
        wins_a=80,
    )
    text = render_evolve_report([tied, behind])
    assert "Mean gap" in text
    # tied game: gap 0; behind: 40% -> gap 10; mean 5.0
    assert "5.0" in text
