from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.cards.registry import get_card
from tests.utils import DummyAI


def test_setup_supply_two_players():
    players = [PlayerState(DummyAI()) for _ in range(2)]
    state = GameState(players)
    state.setup_supply([get_card("Village")])

    # Basic supply counts
    assert state.supply["Copper"] == 60 - 7 * 2
    assert state.supply["Silver"] == 40
    assert state.supply["Gold"] == 30
    assert state.supply["Estate"] == 8
    assert state.supply["Duchy"] == 8
    assert state.supply["Province"] == 8
    assert state.supply["Curse"] == 10

    # Kingdom card supply default is 10
    assert state.supply["Village"] == 10


def test_player_is_stuck_no_cards_no_supply():
    player = PlayerState(DummyAI())
    state = GameState([player])
    state.supply = {"Copper": 0}
    assert state.player_is_stuck(player)
