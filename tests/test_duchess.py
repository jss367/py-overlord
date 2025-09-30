from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _setup_player_and_state():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.supply = {"Duchess": 10, "Duchy": 8}
    return state, player


def test_gaining_duchess_does_not_gain_duchy():
    state, player = _setup_player_and_state()

    duchess = get_card("Duchess")
    state.supply["Duchess"] -= 1
    gained = state.gain_card(player, duchess)

    assert gained.name == "Duchess"
    assert all(card.name != "Duchy" for card in player.discard)
    assert state.supply["Duchy"] == 8


def test_gaining_duchy_gains_duchess_if_available():
    state, player = _setup_player_and_state()

    duchy = get_card("Duchy")
    state.supply["Duchy"] -= 1
    gained = state.gain_card(player, duchy)

    names_in_discard = [card.name for card in player.discard]
    assert gained.name == "Duchy"
    assert names_in_discard.count("Duchy") == 1
    assert names_in_discard.count("Duchess") == 1
    assert state.supply["Duchess"] == 9


def test_gaining_duchy_when_no_duchess_available():
    state, player = _setup_player_and_state()
    state.supply["Duchess"] = 0

    duchy = get_card("Duchy")
    state.supply["Duchy"] -= 1
    gained = state.gain_card(player, duchy)

    assert gained.name == "Duchy"
    assert all(card.name != "Duchess" for card in player.discard)
    assert state.supply["Duchess"] == 0
