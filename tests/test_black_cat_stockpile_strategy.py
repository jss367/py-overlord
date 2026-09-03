"""Tests for the best-found Black Cat and Stockpile strategy."""

from pathlib import Path

from dominion.boards.loader import load_board
from dominion.reporting.catalog_pages import render_catalog_pages
from dominion.strategy.strategy_loader import StrategyLoader


STRATEGY_NAME = "Black Cat Stockpile Best Found"


def test_best_found_strategy_is_registered_with_winning_policy():
    strategy = StrategyLoader().get_strategy(STRATEGY_NAME)

    assert strategy is not None
    assert [rule.card for rule in strategy.gain_priority] == [
        "Bounty Hunter",
        "Province",
        "Duchy",
        "Stockpile",
        "Gold",
        "Black Cat",
        "Silver",
        "Estate",
    ]
    assert [rule.card for rule in strategy.action_priority] == [
        "Bounty Hunter",
        "Black Cat",
    ]
    assert strategy.way_policy == []

    conditions = {rule.card: rule.condition for rule in strategy.gain_priority}
    assert "max_in_deck('Bounty Hunter', 1)" in conditions["Bounty Hunter"]._source
    assert "turn_number('<=', 2)" in conditions["Bounty Hunter"]._source
    assert conditions["Duchy"]._source == "PriorityRule.provinces_left('<=', 2)"
    assert conditions["Black Cat"]._source == (
        "PriorityRule.max_in_deck('Black Cat', 8)"
    )


def test_best_found_strategy_catalog_page_links_target_board(tmp_path):
    board_path = Path("boards/black_cat_and_livery.txt")
    board = load_board(board_path)
    assert {"Black Cat", "Stockpile", "Bounty Hunter"}.issubset(
        board.kingdom_cards
    )

    render_catalog_pages(
        tmp_path,
        board_paths=[board_path],
        strategy_names=[STRATEGY_NAME],
    )

    strategy_page = (
        tmp_path / "strategies" / "black-cat-stockpile-best-found.html"
    ).read_text(encoding="utf-8")
    board_page = (
        tmp_path / "boards" / "black-cat-and-livery.html"
    ).read_text(encoding="utf-8")

    assert "build a Stockpile battery" in strategy_page
    assert "Provinces remaining: at most 2" in strategy_page
    assert 'href="../boards/black-cat-and-livery.html"' in strategy_page
    assert 'href="../strategies/black-cat-stockpile-best-found.html"' in board_page
