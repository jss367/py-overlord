from dominion.game.game_state import GameState
from dominion.cards.registry import get_card
from dominion.events import (
    GainSilver,
    Looting,
    Desperation,
    Delay,
    SeizeTheDay,
)
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

class ChooseFirstActionAI(BuyEventAI):
    def choose_action(self, state, choices):
        for ch in choices:
            if ch is not None:
                return ch
        return None


def test_event_desperation():
    ai = BuyEventAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], events=[Desperation()])
    player = state.players[0]
    player.coins = 0
    state.phase = "buy"
    curses_before = state.supply["Curse"]
    state.handle_buy_phase()
    assert state.supply["Curse"] == curses_before - 1
    assert any(c.name == "Curse" for c in player.discard)


def test_event_seize_the_day_extra_turn():
    ai = BuyEventAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], events=[SeizeTheDay()])
    player = state.players[0]
    player.coins = 4
    state.phase = "buy"
    state.handle_buy_phase()
    assert state.extra_turn
    state.handle_cleanup_phase()
    assert state.current_player is player
    state.handle_start_phase()
    assert player.turns_taken == 2


def test_event_delay_returns_card():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], events=[Delay()])
    player = state.players[0]
    player.coins = 2
    state.phase = "buy"
    first = player.hand[0]
    state.handle_buy_phase()
    assert first not in player.hand
    state.handle_cleanup_phase()
    state.handle_start_phase()
    assert first in player.hand
