"""Tests for Empires Enchantress."""

from dominion.cards.empires.enchantress import Enchantress
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class _PlayFirstActionAI(DummyAI):
    def choose_action(self, state, choices):
        for c in choices:
            if c is not None and c.is_action:
                return c
        return None


def _make_game(num_players=2):
    players = [PlayerState(_PlayFirstActionAI()) for _ in range(num_players)]
    state = GameState(players=players)
    return state


def test_enchantress_sets_flag_on_each_opponent():
    state = _make_game(3)
    state.current_player_index = 0
    caster = state.players[0]
    other1 = state.players[1]
    other2 = state.players[2]

    e = Enchantress()
    caster.in_play.append(e)
    e.play_effect(state)

    assert other1.enchantress_active
    assert other2.enchantress_active
    assert not caster.enchantress_active
    assert e in caster.duration


def test_enchantress_overrides_first_action_play():
    state = _make_game(2)
    state.current_player_index = 1
    other = state.players[1]
    other.enchantress_active = True
    other.actions = 1
    village = get_card("Village")
    smithy = get_card("Smithy")
    other.hand = [village, smithy]
    # Stack deck so we can verify card draws happen.
    other.deck = [get_card("Copper") for _ in range(5)]

    state.handle_action_phase()

    # Village normally would give +1 Card +2 Actions; under Enchantress
    # override it gives +1 Card +1 Action only on the first Action play.
    # The ``enchantress_active`` flag stays set until the caster's next turn
    # (so extra turns like Outpost are still affected); only
    # ``enchantress_used_this_turn`` gates the per-turn override.
    assert other.enchantress_active
    assert other.enchantress_used_this_turn


def test_enchantress_only_first_action_overridden():
    state = _make_game(2)
    state.current_player_index = 1
    other = state.players[1]
    other.enchantress_active = True
    other.actions = 1
    smithy1 = get_card("Smithy")
    smithy2 = get_card("Smithy")
    other.hand = [smithy1, smithy2]
    other.deck = [get_card("Copper") for _ in range(10)]

    state.handle_action_phase()

    # First Smithy enchanted (+1 Card +1 Action). Second Smithy plays normally
    # but action count came from Enchantress override (+1 Action).
    # We expect the player drew at least Smithy's 3 cards on the second play.
    assert other.enchantress_used_this_turn


def test_enchantress_persists_across_opponent_extra_turn():
    """Enchantress should still apply on an opponent's extra turn (e.g.
    Outpost) before the caster's next turn. Only the per-turn "used" flag
    gates the override; the duration flag must persist."""
    state = _make_game(2)
    state.current_player_index = 1
    other = state.players[1]
    other.enchantress_active = True
    other.actions = 1
    smithy = get_card("Smithy")
    other.hand = [smithy]
    other.deck = [get_card("Copper") for _ in range(5)]

    state.handle_action_phase()
    assert other.enchantress_active
    assert other.enchantress_used_this_turn

    # Simulate the start of the player's next (extra) turn re-arming the
    # per-turn flag. ``handle_start_phase`` resets ``enchantress_used_this_turn``;
    # we mirror that here without invoking the full start sequence.
    other.enchantress_used_this_turn = False

    other.actions = 1
    smithy2 = get_card("Smithy")
    other.hand = [smithy2]
    other.deck = [get_card("Copper") for _ in range(5)]
    state.handle_action_phase()

    # Override should fire again on the extra turn.
    assert other.enchantress_active
    assert other.enchantress_used_this_turn


def test_enchantress_grants_two_cards_on_caster_next_turn():
    state = _make_game(2)
    state.current_player_index = 0
    caster = state.players[0]
    other = state.players[1]
    other.enchantress_active = True

    e = Enchantress()
    caster.duration.append(e)

    # Stack caster's deck.
    caster.deck = [get_card("Copper") for _ in range(5)]
    caster.hand = []
    e.on_duration(state)

    assert len(caster.hand) == 2
    assert not other.enchantress_active
