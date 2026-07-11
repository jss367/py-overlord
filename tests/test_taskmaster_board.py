from pathlib import Path

from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import DummyAI


def test_taskmaster_workforce_board_loads():
    board = load_board(Path("boards/taskmaster_workforce.txt"))

    assert board.kingdom_cards == [
        "Taskmaster",
        "Supplies",
        "Groom",
        "Ironworks",
        "Sculptor",
        "Wharf",
        "Market",
        "Festival",
        "Laboratory",
        "Lost City",
    ]
    assert [get_card(name).name for name in board.kingdom_cards] == board.kingdom_cards

    state = GameState(players=[])
    state.initialize_game(
        [DummyAI(), DummyAI()],
        [get_card(name) for name in board.kingdom_cards],
    )

    assert state.supply["Horse"] == 30
    assert "Horse" in state.non_supply_pile_names
