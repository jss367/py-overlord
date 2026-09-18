from compare_all_strategies import _missing_board_components
import pytest
from dominion.boards.loader import BoardConfig
from dominion.simulation.strategy_battle import (
    StrategyBattle,
    StrategyBoardReferences,
    landscape_names,
)


def test_board_compatibility_canonicalizes_parametric_way_names():
    board = BoardConfig(
        kingdom_cards=["Flag Bearer", "Village"],
        ways=["Way of the Mouse (Native Village)"],
    )
    refs = StrategyBoardReferences(
        kingdom_cards=["Flag Bearer"],
        events=[],
        projects=[],
        ways=["Way of the Mouse"],
        landmarks=[],
        allies=[],
    )

    assert _missing_board_components(refs, board, set(board.kingdom_cards)) == []


def test_board_compatibility_canonicalizes_parametric_obelisk_name():
    board = BoardConfig(
        kingdom_cards=["Temple", "Village"],
        landmarks=["Obelisk (Temple)"],
    )
    refs = StrategyBoardReferences(
        kingdom_cards=["Temple"],
        events=[],
        projects=[],
        ways=[],
        landmarks=["Obelisk"],
        allies=[],
    )

    assert _missing_board_components(refs, board, set(board.kingdom_cards)) == []


def test_only_obelisk_is_treated_as_parametric_landmark_reference():
    battle = StrategyBattle()

    refs = battle._split_board_references({"Bandit Fort (Village)"})

    assert refs.landmarks == []
    assert refs.kingdom_cards == ["Bandit Fort (Village)"]


def test_failed_pairing_preserves_existing_reports(tmp_path, monkeypatch):
    import sys
    from compare_all_strategies import main

    output = tmp_path / "leaderboard.html"
    usage = tmp_path / "card-strategy-usage.html"
    output.write_text("previous standings")
    usage.write_text("previous card ranks")
    monkeypatch.setattr(sys, "argv", ["compare_all_strategies.py", "--output", str(output)])
    monkeypatch.setattr(
        "dominion.strategy.strategy_loader.StrategyLoader.list_strategies",
        lambda self: ["Big Money", "Chapel Witch"],
    )

    def fail_pairing(self, *args):
        raise KeyError("Tea House")

    monkeypatch.setattr(StrategyBattle, "run_battle", fail_pairing)
    with pytest.raises(RuntimeError, match="Incomplete results cannot be ranked"):
        main()
    assert output.read_text() == "previous standings"
    assert usage.read_text() == "previous card ranks"


def test_landscape_names_flattens_every_landscape_kind_canonically():
    refs = StrategyBoardReferences(
        kingdom_cards=["Temple"],
        events=["Seaway"],
        projects=["Sewers"],
        ways=["Way of the Mouse (Moat)"],
        landmarks=["Obelisk (Temple)", "Museum"],
        allies=["City-state"],
    )

    assert landscape_names(refs) == [
        "Seaway", "Sewers", "Way of the Mouse", "Obelisk", "Museum", "City-state",
    ]


def test_landscape_names_are_absent_from_the_card_list():
    """The leaderboard filter reads cards and landscapes from separate keys."""

    battle = StrategyBattle()
    refs = battle._split_board_references({"Village", "Museum", "Seaway"})

    assert refs.kingdom_cards == ["Village"]
    assert landscape_names(refs) == ["Seaway", "Museum"]


def test_tournament_metadata_records_landscapes_beside_cards():
    battle = StrategyBattle()
    strategy = battle.strategy_loader.get_strategy("Ninja Watchtower Figurine Money")
    try:
        refs = battle._split_board_references(
            battle._extract_cards_from_strategy(strategy)
        )
    finally:
        battle.close()

    assert "Museum" in landscape_names(refs)
    assert "Museum" not in refs.kingdom_cards
