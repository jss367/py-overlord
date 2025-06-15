from dominion.game.game_state import GameState
from dominion.cards.registry import get_card
from dominion.events import GainSilver
from dominion.projects import CardDraw
from tests.utils import BuyEventAI


def test_event_gain_silver():
    ai = BuyEventAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], events=[GainSilver()])
    player = state.players[0]
    player.coins = 4
    state.phase = "buy"
    state.handle_buy_phase()
    assert any(card.name == "Silver" for card in player.discard)


def test_project_card_draw():
    ai = BuyEventAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], projects=[CardDraw()])
    player = state.players[0]
    player.coins = 5
    state.phase = "buy"
    state.handle_buy_phase()
    assert len(player.projects) == 1
    state.handle_cleanup_phase()
    state.handle_start_phase()
    assert len(player.hand) == 6
