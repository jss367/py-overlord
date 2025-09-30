from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _make_player_with_actions(action_count: int) -> tuple[GameState, PlayerState]:
    player = PlayerState(DummyAI())
    player.in_play = [get_card("Village") for _ in range(action_count)]
    state = GameState(players=[player])
    return state, player


def test_emporium_grants_vp_tokens_when_five_actions_in_play():
    state, player = _make_player_with_actions(5)
    emporium = get_card("Emporium")

    state.gain_card(player, emporium)

    assert player.vp_tokens == 2


def test_emporium_grants_no_bonus_with_fewer_than_five_actions():
    state, player = _make_player_with_actions(4)
    emporium = get_card("Emporium")

    state.gain_card(player, emporium)

    assert player.vp_tokens == 0
