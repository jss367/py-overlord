from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


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
    ]
    for name in names:
        card = get_card(name)
        assert card.name == name


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
