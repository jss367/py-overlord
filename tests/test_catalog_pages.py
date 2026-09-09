from pathlib import Path
from dataclasses import replace

import pytest

from dominion.boards.loader import BoardConfig
from dominion.reporting.board_pages import RenderedBoard, render_board_page, render_board_index
from dominion.reporting.catalog_pages import (
    render_catalog_pages,
    strategy_is_compatible,
)
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


def test_board_tiles_keep_printed_costs_and_separate_basic_piles():
    board = RenderedBoard(
        display_name="Discounted Kingdom",
        page_path=Path("discounted.html"),
        source_path=Path("boards/discounted.txt"),
        config=BoardConfig(
            ["Village", "City Quarter", "Alchemist", "Colony", "Platinum"],
            card_cost_reduction=1,
        ),
    )

    html = render_board_page(board, index_href="index.html")
    assert '<strong>3</strong> Kingdom cards' in html
    assert "Additional basic piles" in html
    assert 'aria-label="3 coins">3</span>' in html
    assert "8 debt" in html
    assert "1 potion" in html
    assert "Card cost reduction: 1 coin." in html
    assert "Tiles show printed costs" in html
    assert "No landscapes specified" in html
    assert "No compatible strategies" in html


def test_board_landscapes_are_visible_searchable_and_escaped():
    board = RenderedBoard(
        display_name='A <special> Kingdom',
        page_path=Path("special.html"),
        source_path=Path("boards/special.txt"),
        config=BoardConfig(
            ["Village"],
            events=["Continue"],
            projects=["Guildhall"],
            ways=["Way of the Mouse (Native Village)"],
            landmarks=["Obelisk (Village)"],
            allies=["League of Shopkeepers"],
            traits={"Village": 'Friendly <script>alert("trait")</script>'},
            prophecy="Kind Emperor",
        ),
    )

    html = render_board_page(board, index_href="index.html")
    index = render_board_index([board], strategy_index_href="../strategies/index.html")
    for page in (html, index):
        for name in ("Continue", "Guildhall", "Native Village", "Obelisk", "League of Shopkeepers", "Kind Emperor"):
            assert name in page
        assert "A &lt;special&gt; Kingdom" in page
        assert "Friendly &lt;script&gt;" in page
        assert '<script>alert("trait")</script>' not in page
    # Setup is readable without opening a disclosure or running JavaScript.
    assert html.index('<article class="landscape-panel">') < html.index('<details class="board-source">')
    assert 'id="board-results" role="status"' in index


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
            "Kingdom Cards": ["Bustling Village", "Horse", "Lich", "Will-o'-Wisp"],
        },
    )
    board = RenderedBoard(
        display_name="Setup Piles",
        page_path=Path("setup-piles.html"),
        source_path=Path("boards/setup_piles.txt"),
        config=BoardConfig(["Settlers", "Student", "Supplies", "Tracker"]),
    )

    assert strategy_is_compatible(strategy, board)


def test_compatibility_canonicalizes_card_aliases_and_parametric_landscapes():
    strategy = collect_rendered_strategies(names=["Big Money"])[0]
    strategy = replace(
        strategy,
        references={
            **strategy.references,
            "Kingdom Cards": ["City Quarter", "Council room", "Potion", "Small Castle"],
            "Ways": ["Way of the Mouse"],
            "Landmarks": ["Obelisk"],
        },
    )
    board = RenderedBoard(
        display_name="Canonical Names",
        page_path=Path("canonical-names.html"),
        source_path=Path("boards/canonical_names.txt"),
        config=BoardConfig(
            ["Black Market", "City quarter", "Castles", "Council Room"],
            ways=["Way of the Mouse (Native Village)"],
            landmarks=["Obelisk (Temple)"],
        ),
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
        "strategies/cursed-band-biding-time-strategy-guide.html",
        "strategies/tea-house-kind-emperor-strategy-guide.html",
        "strategies/mine-guildhall-strategy-guide.html",
        "strategies/kimberley-mine-engine-strategy-guide.html",
        "strategies/hyderabad-strategy-guide.html",
        "strategies/lisbon-strategy-guide.html",
        "strategies/oslo-strategy-guide.html",
        "strategies/port-moresby-strategy-guide.html",
        "strategies/index.html",
        "strategies/card-strategy-usage.html",
        "strategies/leaderboard.html",
        "strategies/village-smithy-lab.html",
    }

    strategy = (output / "strategies" / "village-smithy-lab.html").read_text()
    compatible_board = (output / "boards" / "sample-board.html").read_text()
    incompatible_board = (output / "boards" / "nested" / "other-board.html").read_text()

    assert 'href="../boards/sample-board.html">Sample Board</a>' in strategy
    assert "Other Board" not in strategy
    assert (
        'href="../strategies/village-smithy-lab.html">Village Smithy Lab</a>'
        in compatible_board
    )
    assert "Village Smithy Lab" not in incompatible_board
    assert 'href="../../strategies/big-money.html">Big Money</a>' in incompatible_board
    assert 'class="card-chip type-action"' in compatible_board
    assert "Setup details" in compatible_board


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
    strategy_page = (output / "strategies" / "big-money.html").read_text()
    leaderboard = (output / "strategies" / "leaderboard.html").read_text()
    board_index = (output / "boards" / "index.html").read_text()
    assert 'href="../boards/index.html">Board index</a>' in strategy_index
    assert 'href="leaderboard.html">Leaderboard</a>' in strategy_index
    assert 'href="leaderboard.html">Leaderboard</a>' in strategy_page
    assert "No tournament results yet" in leaderboard
    assert 'href="index.html">Strategy index</a>' in leaderboard
    assert 'href="../strategies/index.html">Strategy index</a>' in board_index


def test_catalog_replaces_a_stale_leaderboard_placeholder(tmp_path):
    boards_root = tmp_path / "boards"
    board = _write_board(boards_root / "simple.txt", "Village\n")
    output = tmp_path / "site"
    output.mkdir()
    leaderboard = output / "strategies" / "leaderboard.html"
    leaderboard.parent.mkdir()
    leaderboard.write_text("completed tournament", encoding="utf-8")

    written = render_catalog_pages(
        output,
        boards_root=boards_root,
        board_paths=[board],
        strategy_names=["Big Money"],
    )

    html = leaderboard.read_text(encoding="utf-8")
    assert "completed tournament" not in html
    assert "No tournament results yet" in html
    assert leaderboard in written


@pytest.mark.parametrize(
    ("filename", "title"),
    [
        ("cursed-band-biding-time-strategy-guide.html", "Cursed Band and Biding Time Strategy Guide"),
        ("hyderabad-strategy-guide.html", "Hyderabad Strategy Search Guide"),
        ("lisbon-strategy-guide.html", "Lisbon Strategy Search Guide"),
        ("oslo-strategy-guide.html", "Discounted Oslo Strategy Search Guide"),
        ("port-moresby-strategy-guide.html", "Port Moresby Strategy Search Guide"),
    ],
)
def test_catalog_writes_curated_strategy_guide_to_clean_output(tmp_path, filename, title):
    boards_root = tmp_path / "boards"
    board = _write_board(boards_root / "simple.txt", "Village\n")
    output = tmp_path / "site"
    guide = output / "strategies" / filename

    written = render_catalog_pages(
        output,
        boards_root=boards_root,
        board_paths=[board],
        strategy_names=["Big Money"],
    )

    assert guide in written
    assert f"<title>{title}</title>" in guide.read_text(encoding="utf-8")
    source = (
        Path(__file__).resolve().parents[1]
        / "dominion/reporting/curated_strategy_guides"
        / filename
    )
    assert guide.read_bytes() == source.read_bytes()
    strategy_index = (output / "strategies" / "index.html").read_text()
    assert f'href="{filename}"' in strategy_index
