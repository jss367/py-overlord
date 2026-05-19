from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _make_state():
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    state.log_callback = lambda message: None
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    return state, player


def _play_lookout(state, player):
    lookout = get_card("Lookout")
    player.hand = [lookout]
    player.hand.remove(lookout)
    player.in_play.append(lookout)
    lookout.on_play(state)


def test_lookout_trashes_copper_before_province():
    state, player = _make_state()
    province = get_card("Province")
    copper = get_card("Copper")
    silver = get_card("Silver")
    # Top of deck is the end of the list; Lookout reveals Province, Copper, Silver.
    player.deck = [silver, copper, province]

    _play_lookout(state, player)

    assert state.trash == [copper]
    assert province not in state.trash
    assert player.discard == [silver]
    assert player.deck[-1] is province


def test_lookout_trashes_curse_before_estate_and_gold():
    state, player = _make_state()
    curse = get_card("Curse")
    estate = get_card("Estate")
    gold = get_card("Gold")
    player.deck = [gold, estate, curse]

    _play_lookout(state, player)

    assert state.trash == [curse]
    assert estate not in state.trash
    assert gold not in state.trash


def test_lookout_topdecks_best_remaining_card():
    state, player = _make_state()
    curse = get_card("Curse")
    estate = get_card("Estate")
    gold = get_card("Gold")
    player.deck = [gold, estate, curse]

    _play_lookout(state, player)

    assert player.discard == [estate]
    assert player.deck == [gold]
