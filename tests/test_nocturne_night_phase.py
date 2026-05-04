"""Tests for the Night phase: fires between Buy and Cleanup."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class _PlayAllAI(DummyAI):
    def choose_action(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_buy(self, state, choices):
        return None

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c.name in {"Estate", "Curse", "Copper"}:
                return c
        return choices[0] if choices else None

    def choose_night(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_cards_to_trash_for_monastery(self, state, player, choices, count):
        return choices[:count]


def _setup():
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.players = [PlayerState(_PlayAllAI())]
    state.players[0].initialize()
    state.supply = {
        "Copper": 30, "Silver": 20, "Gold": 10, "Curse": 10,
        "Estate": 10, "Duchy": 10, "Province": 8,
        "Will-o'-Wisp": 12, "Imp": 13, "Ghost": 6, "Bat": 10, "Wish": 12,
        "Vampire": 10,
    }
    return state, state.players[0]


def test_night_phase_plays_night_cards():
    state, player = _setup()
    monastery = get_card("Monastery")
    player.cards_gained_this_turn_count = 1
    player.hand = [monastery, get_card("Estate")]
    state.phase = "night"
    state.handle_night_phase()
    # Monastery played → Estate trashed
    assert any(c.name == "Estate" for c in state.trash)
    assert state.phase == "cleanup"


def test_night_phase_skips_when_no_night_cards():
    state, player = _setup()
    player.hand = [get_card("Copper")]
    state.phase = "night"
    state.handle_night_phase()
    assert state.phase == "cleanup"


def test_buy_phase_transitions_to_night():
    state, player = _setup()
    player.coins = 0
    player.buys = 0
    state.phase = "buy"
    state.handle_buy_phase()
    # Should now be in night phase
    assert state.phase == "night"


def test_full_turn_flow_includes_night():
    """Buy → Night → Cleanup; verify phase transitions don't drop Night."""

    state, player = _setup()
    player.hand = [get_card("Copper")]
    state.phase = "buy"
    player.coins = 0
    player.buys = 0
    # Run buy phase
    state.handle_buy_phase()
    assert state.phase == "night"
    # Run night phase
    state.handle_night_phase()
    assert state.phase == "cleanup"
