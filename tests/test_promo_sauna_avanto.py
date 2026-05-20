from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _state() -> tuple[GameState, PlayerState]:
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    return state, player


def test_avanto_partner_sauna_respects_warlord_block():
    state, player = _state()
    player.warlord_restriction_count = 1
    avanto = get_card("Avanto")
    blocked_sauna = get_card("Sauna")
    player.in_play = [avanto, get_card("Sauna"), get_card("Sauna")]
    player.hand = [blocked_sauna]
    player.deck = [get_card("Copper")]

    avanto.play_effect(state)

    assert blocked_sauna in player.hand
    assert blocked_sauna not in player.in_play
    assert len(player.deck) == 1
    assert player.actions_this_turn == 0


def test_sauna_partner_avanto_respects_warlord_block():
    state, player = _state()
    player.warlord_restriction_count = 1
    sauna = get_card("Sauna")
    blocked_avanto = get_card("Avanto")
    player.in_play = [sauna, get_card("Avanto"), get_card("Avanto")]
    player.hand = [blocked_avanto]
    player.deck = [get_card("Copper") for _ in range(3)]

    sauna.play_effect(state)

    assert blocked_avanto in player.hand
    assert blocked_avanto not in player.in_play
    assert len(player.deck) == 3
    assert player.actions_this_turn == 0
