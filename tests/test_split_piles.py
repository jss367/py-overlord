from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.cards.registry import get_card
from tests.utils import DummyAI


def test_patrician_emporium_supply_and_buy_rule():
    players = [PlayerState(DummyAI()) for _ in range(2)]
    state = GameState(players)
    state.setup_supply([get_card("Patrician")])

    # Split pile should start with five of each card
    assert state.supply["Patrician"] == 5
    assert state.supply["Emporium"] == 5

    emp = get_card("Emporium")
    # Cannot buy Emporium while Patricians remain
    assert not emp.may_be_bought(state)

    state.supply["Patrician"] = 0
    # Once Patricians are gone Emporium becomes available
    assert emp.may_be_bought(state)


def test_split_pile_counts_as_single_empty_pile():
    players = [PlayerState(DummyAI()) for _ in range(2)]
    state = GameState(players)
    state.setup_supply([get_card("Patrician"), get_card("Village")])

    # Deplete two other piles
    state.supply["Copper"] = 0
    state.supply["Village"] = 0

    # Deplete top half only
    state.supply["Patrician"] = 0
    assert state.empty_piles == 2
    assert not state.is_game_over()

    # Deplete bottom half as well
    state.supply["Emporium"] = 0
    assert state.empty_piles == 3
    assert state.is_game_over()
