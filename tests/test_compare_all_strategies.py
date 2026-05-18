from compare_all_strategies import _missing_board_components
from dominion.boards.loader import BoardConfig
from dominion.simulation.strategy_battle import StrategyBattle, StrategyBoardReferences


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
