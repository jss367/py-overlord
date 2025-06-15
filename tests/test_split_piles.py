from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.cards.registry import get_card
from tests.utils import DummyAI


def test_patrician_emporium_supply_and_buy_rule():
    players = [PlayerState(DummyAI()) for _ in range(2)]
    state = GameState(players)
    state.setup_supply([get_card("Patrician"), get_card("Emporium")])

    # Split pile should start with five of each card
    assert state.supply["Patrician"] == 5
    assert state.supply["Emporium"] == 5

    emp = get_card("Emporium")
    # Cannot buy Emporium while Patricians remain
    assert not emp.may_be_bought(state)

    state.supply["Patrician"] = 0
    # Once Patricians are gone Emporium becomes available
    assert emp.may_be_bought(state)
