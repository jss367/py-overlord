from compare_all_strategies import _missing_board_components
from dominion.boards.loader import BoardConfig
from dominion.simulation.strategy_battle import StrategyBoardReferences


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
        allies=[],
    )

    assert _missing_board_components(refs, board, set(board.kingdom_cards)) == []
