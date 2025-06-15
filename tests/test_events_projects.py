from dominion.game.game_state import GameState
from dominion.cards.registry import get_card
from dominion.events import GainSilver, Looting
from dominion.projects import CardDraw, Sewers
from tests.utils import BuyEventAI, TrashFirstAI


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


from dominion.cards.plunder import LOOT_CARD_NAMES


def test_event_looting_gain_loot():
    ai = BuyEventAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], events=[Looting()])
    player = state.players[0]
    player.coins = 5
    state.phase = "buy"
    state.handle_buy_phase()
    assert any(card.name in LOOT_CARD_NAMES for card in player.discard)


def test_project_sewers_trash_extra():
    ai = TrashFirstAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], projects=[Sewers()])
    player = state.players[0]
    player.coins = 3
    state.phase = "buy"
    state.handle_buy_phase()
    assert len(player.projects) == 1

    # Prepare hand with two cards to trash
    player.hand = [get_card("Estate"), get_card("Copper")]
    first = player.hand.pop(0)
    state.trash_card(player, first)
    assert len(state.trash) == 2
