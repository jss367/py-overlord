from pathlib import Path

import pytest

from dominion.boards.loader import BoardConfig, load_board
from dominion.simulation.strategy_battle import StrategyBattle


def write_board(tmp_path: Path, contents: str) -> Path:
    board_path = tmp_path / "board.txt"
    board_path.write_text(contents, encoding="utf-8")
    return board_path


def test_load_board_parses_kingdom_and_landscapes(tmp_path):
    path = write_board(
        tmp_path,
        """
        # Comment line
        Bridge
        Ironmonger

        Way: Way of the Butterfly
        Project: Innovation
        Event: Gamble
        """,
    )

    board = load_board(path)

    assert board.kingdom_cards == ["Bridge", "Ironmonger"]
    assert board.ways == ["Way of the Butterfly"]
    assert board.projects == ["Innovation"]
    assert board.events == ["Gamble"]


def test_strategy_battle_prepares_landscapes(tmp_path):
    path = write_board(
        tmp_path,
        """
        Bridge
        Ironmonger
        Way: Way of the Butterfly
        Project: Innovation
        """,
    )

    board = load_board(path)
    battle = StrategyBattle(board_config=board)

    kingdom, events, projects, ways = battle._prepare_board_components(board.kingdom_cards)

    assert [card.name for card in kingdom] == board.kingdom_cards
    assert events == []
    assert [project.name for project in projects] == board.projects
    assert [way.name for way in ways] == board.ways


def test_load_board_requires_cards(tmp_path):
    path = write_board(tmp_path, "# Only comments")

    with pytest.raises(ValueError):
        load_board(path)


def test_board_config_defaults():
    config = BoardConfig(["Village"])

    assert config.events == []
    assert config.projects == []
    assert config.ways == []


def test_load_board_handles_prosperity_supply(tmp_path):
    path = write_board(
        tmp_path,
        """
        Bank
        Grand Market
        Colony
        Platinum
        """,
    )

    board = load_board(path)

    assert board.kingdom_cards == [
        "Bank",
        "Grand Market",
        "Colony",
        "Platinum",
    ]
    assert board.events == []
    assert board.projects == []
    assert board.ways == []


def test_wealthy_cities_board_lists_prosperity_supply():
    board = load_board(Path("boards/wealthy_cities.txt"))

    assert "Colony" in board.kingdom_cards
    assert "Platinum" in board.kingdom_cards
    assert all("Money:" not in entry for entry in board.kingdom_cards)
