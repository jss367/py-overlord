from pathlib import Path
from dataclasses import replace

from dominion.boards.loader import BoardConfig
from dominion.reporting.board_pages import RenderedBoard
from dominion.reporting.catalog_pages import render_catalog_pages, strategy_is_compatible
from dominion.reporting.strategy_links import board_display_name, board_page_path
from dominion.reporting.strategy_pages import collect_rendered_strategies


def _write_board(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_board_names_expand_big_money_shorthand():
    path = Path("boards/calibration/smithy_bm.txt")

    assert board_display_name(path) == "Smithy Big Money"
    assert board_page_path(path) == Path("calibration/smithy-big-money.html")


def test_compatibility_requires_referenced_landscapes():
    strategy = collect_rendered_strategies(names=["Big Money"])[0]
    strategy = replace(
        strategy,
        references={**strategy.references, "Events": ["Continue"]},
    )
    board = RenderedBoard(
        display_name="Sample",
        page_path=Path("sample.html"),
        source_path=Path("boards/sample.txt"),
        config=BoardConfig(["Village"]),
    )

    assert not strategy_is_compatible(strategy, board)
    board.config.events.append("Continue")
    assert strategy_is_compatible(strategy, board)


def test_compatibility_includes_setup_created_piles():
    strategy = collect_rendered_strategies(names=["Big Money"])[0]
    strategy = replace(
        strategy,
        references={
            **strategy.references,
            "Kingdom Cards": ["Bustling Village", "Horse", "Lich"],
        },
    )
    board = RenderedBoard(
        display_name="Setup Piles",
        page_path=Path("setup-piles.html"),
        source_path=Path("boards/setup_piles.txt"),
        config=BoardConfig(["Settlers", "Student", "Supplies"]),
    )

    assert strategy_is_compatible(strategy, board)


def test_catalog_pages_link_compatible_boards_and_strategies_both_ways(tmp_path):
    boards_root = tmp_path / "source_boards"
    compatible = _write_board(
        boards_root / "sample_board.txt",
        "Village\nSmithy\nMarket\nFestival\nLaboratory\nMine\nWitch\nMoat\nWorkshop\nChapel\n",
    )
    incompatible = _write_board(
        boards_root / "nested" / "other_board.txt",
        "Cellar\nMarket\nMerchant\nMilitia\nMine\nMoat\nRemodel\nSmithy\nVillage\nWorkshop\n",
    )
    output = tmp_path / "site"

    written = render_catalog_pages(
        output,
        boards_root=boards_root,
        board_paths=[compatible, incompatible],
        strategy_names=["Big Money", "Village Smithy Lab"],
    )

    assert {path.relative_to(output).as_posix() for path in written} == {
        "boards/index.html",
        "boards/nested/other-board.html",
        "boards/sample-board.html",
        "strategies/big-money.html",
        "strategies/index.html",
        "strategies/village-smithy-lab.html",
    }

    strategy = (output / "strategies" / "village-smithy-lab.html").read_text()
    compatible_board = (output / "boards" / "sample-board.html").read_text()
    incompatible_board = (output / "boards" / "nested" / "other-board.html").read_text()

    assert 'href="../boards/sample-board.html">Sample Board</a>' in strategy
    assert "Other Board" not in strategy
    assert 'href="../strategies/village-smithy-lab.html">Village Smithy Lab</a>' in compatible_board
    assert "Village Smithy Lab" not in incompatible_board
    assert 'href="../../strategies/big-money.html">Big Money</a>' in incompatible_board


def test_catalog_indexes_link_to_each_other(tmp_path):
    boards_root = tmp_path / "boards"
    board = _write_board(boards_root / "simple.txt", "Village\n")
    output = tmp_path / "site"

    render_catalog_pages(
        output,
        boards_root=boards_root,
        board_paths=[board],
        strategy_names=["Big Money"],
    )

    strategy_index = (output / "strategies" / "index.html").read_text()
    board_index = (output / "boards" / "index.html").read_text()
    assert 'href="../boards/index.html">Board index</a>' in strategy_index
    assert 'href="../strategies/index.html">Strategy index</a>' in board_index
