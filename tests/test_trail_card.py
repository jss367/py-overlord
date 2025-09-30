from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


class DeclineTrailAI(ChooseFirstActionAI):
    """AI that declines optional Trail reactions."""

    def choose_action(self, state, choices):
        non_none = [card for card in choices if card is not None]
        if non_none and all(card.name == "Trail" for card in non_none):
            return None
        return super().choose_action(state, choices)


def _setup_game(ai):
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Trail")])
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.actions = 0
    player.actions_this_turn = 0
    player.actions_played = 0
    return state, player


def test_trail_reacts_to_discard():
    ai = ChooseFirstActionAI()
    state, player = _setup_game(ai)

    trail = get_card("Trail")
    player.hand = [trail]
    player.deck = [get_card("Copper")]

    player.hand.remove(trail)
    state.discard_card(player, trail)

    assert trail in player.in_play
    assert trail not in player.discard
    assert player.actions == 1
    assert player.actions_this_turn == 1
    assert player.actions_played == 1
    assert len(player.hand) == 1  # Drew one card


def test_trail_discard_reaction_can_be_declined():
    ai = DeclineTrailAI()
    state, player = _setup_game(ai)

    trail = get_card("Trail")
    player.hand = [trail]

    player.hand.remove(trail)
    state.discard_card(player, trail)

    assert trail in player.discard
    assert trail not in player.in_play
    assert player.actions == 0


def test_trail_can_play_when_gained():
    ai = ChooseFirstActionAI()
    state, player = _setup_game(ai)

    player.deck = [get_card("Copper")]

    gained = state.gain_card(player, get_card("Trail"))

    assert gained in player.in_play
    assert player.actions == 1
    assert player.actions_this_turn == 1
    assert player.actions_played == 1
    assert len(player.hand) == 1


def test_trail_gain_reaction_can_be_declined():
    ai = DeclineTrailAI()
    state, player = _setup_game(ai)

    gained = state.gain_card(player, get_card("Trail"))

    assert gained in player.discard
    assert gained not in player.in_play


def test_trail_trash_reaction_returns_to_trash():
    ai = ChooseFirstActionAI()
    state, player = _setup_game(ai)

    trail = get_card("Trail")
    player.deck = [get_card("Copper")]

    # Simulate the card being trashed from hand
    player.hand = [trail]
    player.hand.remove(trail)

    state.trash_card(player, trail)

    assert trail in state.trash
    assert trail not in player.in_play
    assert player.actions == 1
    assert player.actions_this_turn == 1
    assert player.actions_played == 1
    assert len(player.hand) == 1
