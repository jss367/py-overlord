from __future__ import annotations

from pathlib import Path

from dominion.analysis import landscape_sanity
from dominion.analysis.landscape_sanity import (
    LandscapePiece,
    MatchupStats,
    analyze_landscapes,
    landscape_pieces,
    render_markdown,
    render_table,
    without_landscape_piece,
)
from dominion.boards.loader import BoardConfig, load_board


REPO_ROOT = Path(__file__).resolve().parent.parent
VICTORIA_BOARD = REPO_ROOT / "boards" / "victoria_kingdom.txt"


def test_landscape_pieces_returns_events_projects_and_ways_in_order():
    board = BoardConfig(
        kingdom_cards=["Village"],
        events=["Windfall"],
        projects=["Innovation"],
        ways=["Way of the Butterfly"],
        landmarks=["Keep"],
    )

    assert landscape_pieces(board) == [
        LandscapePiece("Event", "Windfall"),
        LandscapePiece("Project", "Innovation"),
        LandscapePiece("Way", "Way of the Butterfly"),
    ]


def test_without_landscape_piece_removes_only_requested_piece():
    board = BoardConfig(
        kingdom_cards=["Flag Bearer"],
        events=["Windfall", "Training"],
        projects=["Innovation"],
        ways=["Way of the Butterfly"],
        allies=["League of Shopkeepers"],
        traits={"Flag Bearer": "Tireless"},
    )

    stripped = without_landscape_piece(board, LandscapePiece("Event", "Windfall"))

    assert stripped.events == ["Training"]
    assert stripped.projects == ["Innovation"]
    assert stripped.ways == ["Way of the Butterfly"]
    assert stripped.kingdom_cards == ["Flag Bearer"]
    assert stripped.allies == ["League of Shopkeepers"]
    assert stripped.traits == {"Flag Bearer": "Tireless"}


def test_analyze_landscapes_flags_near_zero_win_rate_delta(monkeypatch):
    board = BoardConfig(
        kingdom_cards=["Stockpile"],
        events=["Windfall"],
        ways=["Way of the Butterfly"],
    )
    calls: list[BoardConfig] = []

    def fake_run(strategy, opponent, board_config, games, *, seed, use_shelters):
        calls.append(board_config)
        if board_config.events and board_config.ways:
            return MatchupStats(games=games, wins=10, win_rate=100.0, avg_score=50.0)
        if not board_config.events:
            return MatchupStats(games=games, wins=10, win_rate=100.0, avg_score=49.0)
        return MatchupStats(games=games, wins=6, win_rate=60.0, avg_score=34.0)

    monkeypatch.setattr(landscape_sanity, "run_seeded_matchup", fake_run)

    results = analyze_landscapes(
        "VictoriaEngine",
        board,
        opponent_name="Big Money",
        games=10,
        threshold=2.0,
    )

    assert [result.piece.label for result in results] == [
        "Event: Windfall",
        "Way: Way of the Butterfly",
    ]
    assert results[0].win_rate_delta == 0.0
    assert results[0].ignores_landscape is True
    assert results[1].win_rate_delta == 40.0
    assert results[1].ignores_landscape is False
    assert len(calls) == 3


def test_renderers_include_status_and_score_deltas():
    result = landscape_sanity.LandscapeSanityResult(
        piece=LandscapePiece("Event", "Windfall"),
        with_piece=MatchupStats(games=5, wins=5, win_rate=100.0, avg_score=42.2),
        without_piece=MatchupStats(games=5, wins=5, win_rate=100.0, avg_score=41.1),
        threshold=2.0,
    )

    table = render_table([result])
    markdown = render_markdown([result])

    assert "Event: Windfall" in table
    assert "+0.0%" in table
    assert "+1.1" in table
    assert "ignores landscape" in table
    assert "| Event: Windfall |" in markdown


def test_main_smoke_runs_victoria_board_with_one_game(capsys):
    exit_code = landscape_sanity.main(
        [
            "--strategy",
            "VictoriaEngine",
            "--board",
            str(VICTORIA_BOARD),
            "--games",
            "1",
            "--seed",
            "233",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Event: Windfall" in output
    assert "Way: Way of the Butterfly" in output


def test_load_victoria_board_has_expected_landscapes():
    board = load_board(VICTORIA_BOARD)

    assert landscape_pieces(board) == [
        LandscapePiece("Event", "Windfall"),
        LandscapePiece("Way", "Way of the Butterfly"),
    ]
