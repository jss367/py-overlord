from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _make_state_with_player() -> tuple[GameState, PlayerState]:
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    return state, player


def test_plunder_gain_also_gains_gold():
    state, player = _make_state_with_player()
    plunder = get_card("Plunder")

    state.supply[plunder.name] = 1
    state.supply["Gold"] = 5

    state.supply[plunder.name] -= 1
    state.gain_card(player, plunder)

    assert any(card.name == "Gold" for card in player.discard)
    assert state.supply["Gold"] == 4


def test_plunder_play_topdecks_gold():
    state, player = _make_state_with_player()
    plunder = get_card("Plunder")

    state.supply["Gold"] = 5
    player.deck = [get_card("Estate")]

    plunder.on_play(state)

    assert player.deck[0].name == "Gold"
    assert len(player.deck) == 2
    assert player.deck[1].name == "Estate"
    assert state.supply["Gold"] == 4


def test_plunder_play_does_nothing_when_gold_empty():
    state, player = _make_state_with_player()
    plunder = get_card("Plunder")

    state.supply["Gold"] = 0
    player.deck = []

    plunder.on_play(state)

    assert player.deck == []
    assert state.supply["Gold"] == 0
