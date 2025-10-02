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


class StopAfterOneVillageAI(ChooseFirstActionAI):
    """AI that stops First Mate after playing a single copy of the named card."""

    def __init__(self):
        super().__init__()
        self._first_mate_resolution_calls = 0

    def choose_action(self, state, choices):
        non_none = [c for c in choices if c is not None]
        if non_none and all(card.name == "Village" for card in non_none):
            if self._first_mate_resolution_calls == 0:
                self._first_mate_resolution_calls += 1
                return non_none[0]
            return None

        self._first_mate_resolution_calls = 0
        return super().choose_action(state, choices)


def test_new_card_registry():
    names = [
        "Trail",
        "Acting Troupe",
        "Taskmaster",
        "Trader",
        "Torturer",
        "Patrol",
        "Inn",
        "First Mate",
        "Messenger",
    ]
    for name in names:
        card = get_card(name)
        assert card.name == name


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
    state2.initialize_game([MessengerTestAI(discard_deck=False, gain_choice="Silver"), other_ai], [get_card("Messenger")])

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


def test_first_mate_effect():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("First Mate"), get_card("Village")])

    player = state.players[0]

    # Set up a controlled hand and deck
    player.hand = [get_card("First Mate"), get_card("Village"), get_card("Village")]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.actions = 1

    state.phase = "action"
    state.handle_action_phase()

    # Both Villages should have been played
    assert sum(1 for c in player.in_play if c.name == "Village") == 2
    # First Mate should also be in play
    assert any(c.name == "First Mate" for c in player.in_play)
    # Hand should be drawn up to 6 cards
    assert len(player.hand) == 6


def test_first_mate_can_stop_after_first_copy():
    ai = StopAfterOneVillageAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("First Mate"), get_card("Village")])

    player = state.players[0]

    player.hand = [get_card("First Mate"), get_card("Village"), get_card("Village")]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.actions = 1

    state.phase = "action"
    state.handle_action_phase()

    # Only one Village should have been played
    assert sum(1 for c in player.in_play if c.name == "Village") == 1
    # The other Village should remain in hand
    assert any(c.name == "Village" for c in player.hand)
    # Draw-to-six cleanup should still occur
    assert len(player.hand) == 6
