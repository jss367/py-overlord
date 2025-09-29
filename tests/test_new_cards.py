from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI, DummyAI


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
    ]
    for name in names:
        card = get_card(name)
        assert card.name == name


def _make_two_player_state():
    ais = [DummyAI(), DummyAI()]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card("Torturer")])
    return state


def _play_torturer(state):
    torturer = get_card("Torturer")
    torturer.play_effect(state)


def test_torturer_prefers_to_discard_junk():
    state = _make_two_player_state()
    _, opponent = state.players

    opponent.hand = [get_card("Estate"), get_card("Estate"), get_card("Silver")]
    opponent.discard = []

    _play_torturer(state)

    discarded_names = [card.name for card in opponent.discard]
    assert discarded_names.count("Estate") == 2
    assert all(card.name != "Curse" for card in opponent.hand)
    assert len(opponent.hand) == 1


def test_torturer_gives_curse_when_hand_is_strong():
    state = _make_two_player_state()
    _, opponent = state.players

    opponent.hand = [get_card("Gold"), get_card("Laboratory"), get_card("Silver")]
    opponent.discard = []

    _play_torturer(state)

    curse_in_hand = [card for card in opponent.hand if card.name == "Curse"]
    assert len(curse_in_hand) == 1
    assert len(opponent.discard) == 0
    assert len(opponent.hand) == 4


def test_torturer_discards_if_no_curses_available():
    state = _make_two_player_state()
    _, opponent = state.players

    opponent.hand = [get_card("Gold"), get_card("Laboratory"), get_card("Silver")]
    opponent.discard = []
    state.supply["Curse"] = 0

    _play_torturer(state)

    assert len(opponent.discard) == 2
    assert all(card.name != "Curse" for card in opponent.hand)


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
