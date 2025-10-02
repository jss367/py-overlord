"""Tests for cards from the Adventures expansion."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState

from tests.utils import ChooseFirstActionAI


class MessengerTestAI(ChooseFirstActionAI):
    def __init__(self, *, discard_deck: bool, gain_choice: str):
        super().__init__()
        self.discard_deck = discard_deck
        self.gain_choice = gain_choice

    def choose_buy(self, state, choices):
        for choice in choices:
            if choice is None:
                continue
            if choice.name == self.gain_choice:
                return choice
        for choice in choices:
            if choice is not None:
                return choice
        return None

    def should_discard_deck_with_messenger(self, state, player):
        return self.discard_deck


def test_messenger_effects():
    ai = MessengerTestAI(discard_deck=True, gain_choice="Silver")
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Messenger")])

    player = state.players[0]
    player.hand = [get_card("Messenger")]
    player.deck = [get_card("Copper"), get_card("Estate")]
    player.discard = []
    player.actions = 1

    state.phase = "action"
    state.handle_action_phase()

    assert player.deck == []
    assert [card.name for card in player.discard] == ["Copper", "Estate"]
    assert player.buys == 2
    assert player.coins == 2

    other_ai = ChooseFirstActionAI()
    state2 = GameState(players=[])
    state2.initialize_game(
        [MessengerTestAI(discard_deck=False, gain_choice="Silver"), other_ai],
        [get_card("Messenger")],
    )

    current = state2.players[0]
    opponent = state2.players[1]
    current.discard = []
    opponent.discard = []
    state2.phase = "buy"
    state2.current_player_index = 0
    current.cards_gained_this_buy_phase = 0

    initial_silver = state2.supply["Silver"]
    state2.supply["Messenger"] -= 1
    state2.gain_card(current, get_card("Messenger"))

    assert [card.name for card in current.discard].count("Messenger") == 1
    assert [card.name for card in current.discard].count("Silver") == 1
    assert [card.name for card in opponent.discard].count("Silver") == 1
    assert state2.supply["Silver"] == initial_silver - 2
    assert current.cards_gained_this_buy_phase == 2
