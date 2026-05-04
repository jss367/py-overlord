"""Behavioural tests for Hinterlands' Cauldron treasure-attack.

Card text: "+$2, +1 Buy. The third time you gain an Action card on
your turn, each other player gains a Curse."

The trigger lives in
:meth:`dominion.game.game_state.GameState._track_action_gain` and
runs the curse-out through ``attack_player`` so any Reaction
card / Lighthouse / Shield blocks it.
"""

from __future__ import annotations

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import ChooseFirstActionAI


def _make_state(num_players: int = 2) -> GameState:
    players = [PlayerState(ChooseFirstActionAI()) for _ in range(num_players)]
    state = GameState(players=players)
    state.setup_supply([])  # full base supply, plus we'll seed kingdom cards as needed
    for p in players:
        p.hand = []
        p.deck = []
        p.discard = []
        p.in_play = []
        p.duration = []
    state.current_player_index = 0
    return state


def _put_cauldron_in_play(player: PlayerState) -> None:
    """Simulate Cauldron having been played as a Treasure earlier this turn."""
    player.in_play.append(get_card("Cauldron"))


def test_cauldron_card_definition_is_treasure_attack():
    cauldron = get_card("Cauldron")
    assert cauldron.is_treasure
    assert cauldron.is_attack
    assert cauldron.stats.coins == 2
    assert cauldron.stats.buys == 1


def test_cauldron_does_not_fire_on_first_or_second_action_gain():
    state = _make_state()
    attacker, defender = state.players
    _put_cauldron_in_play(attacker)

    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))

    assert attacker.actions_gained_this_turn == 2
    assert not attacker.cauldron_triggered
    assert not any(c.name == "Curse" for c in defender.discard)


def test_cauldron_fires_on_third_action_gain():
    state = _make_state()
    attacker, defender = state.players
    _put_cauldron_in_play(attacker)

    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))

    assert attacker.actions_gained_this_turn == 3
    assert attacker.cauldron_triggered
    # Defender should have received exactly one Curse.
    curses = sum(1 for c in defender.discard if c.name == "Curse")
    assert curses == 1


def test_cauldron_triggers_only_once_per_turn():
    state = _make_state()
    attacker, defender = state.players
    _put_cauldron_in_play(attacker)

    for _ in range(5):
        state.gain_card(attacker, get_card("Village"))

    curses = sum(1 for c in defender.discard if c.name == "Curse")
    assert curses == 1
    assert attacker.cauldron_triggered


def test_cauldron_skips_non_actions():
    state = _make_state()
    attacker, defender = state.players
    _put_cauldron_in_play(attacker)

    # Treasures and Victory cards do not advance the action-gain counter.
    state.gain_card(attacker, get_card("Silver"))
    state.gain_card(attacker, get_card("Estate"))
    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))

    assert attacker.actions_gained_this_turn == 2
    assert not attacker.cauldron_triggered
    assert not any(c.name == "Curse" for c in defender.discard)


def test_cauldron_requires_cauldron_in_play():
    state = _make_state()
    attacker, defender = state.players
    # No Cauldron in play.

    for _ in range(4):
        state.gain_card(attacker, get_card("Village"))

    assert not attacker.cauldron_triggered
    assert not any(c.name == "Curse" for c in defender.discard)


def test_cauldron_blocked_by_moat():
    state = _make_state()
    attacker, defender = state.players
    _put_cauldron_in_play(attacker)
    defender.hand.append(get_card("Moat"))

    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))

    # Trigger fires (counter and flag) but Moat blocks the curse.
    assert attacker.cauldron_triggered
    assert not any(c.name == "Curse" for c in defender.discard)


def test_cauldron_blocked_by_lighthouse():
    state = _make_state()
    attacker, defender = state.players
    _put_cauldron_in_play(attacker)
    defender.duration.append(get_card("Lighthouse"))

    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))

    assert attacker.cauldron_triggered
    assert not any(c.name == "Curse" for c in defender.discard)


def test_cauldron_counter_resets_at_start_of_turn():
    state = _make_state()
    attacker, defender = state.players
    _put_cauldron_in_play(attacker)

    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))

    assert attacker.cauldron_triggered
    starting_curses = sum(1 for c in defender.discard if c.name == "Curse")
    assert starting_curses == 1

    # Move to the other player and back.
    state.current_player_index = 1
    state.handle_start_phase()
    state.current_player_index = 0
    state.handle_start_phase()

    assert attacker.actions_gained_this_turn == 0
    assert not attacker.cauldron_triggered

    # Now a fresh sequence of 3 action gains should fire the curse again
    # (a second Cauldron play would also persist into in_play in real play;
    # for this test we re-seed the in-play zone).
    attacker.in_play = [get_card("Cauldron")]
    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))

    new_curses = sum(1 for c in defender.discard if c.name == "Curse")
    assert new_curses == starting_curses + 1


def test_cauldron_counter_isolated_per_player():
    state = _make_state(num_players=2)
    p0, p1 = state.players
    _put_cauldron_in_play(p0)

    # Player 1 gaining actions does NOT advance Player 0's counter.
    state.gain_card(p1, get_card("Village"))
    state.gain_card(p1, get_card("Village"))
    state.gain_card(p1, get_card("Village"))

    assert p0.actions_gained_this_turn == 0
    assert p1.actions_gained_this_turn == 3
    # Player 1 has no Cauldron in play, so no curse is delivered.
    assert not any(c.name == "Curse" for c in p0.discard)


def test_cauldron_runs_out_of_curse_supply_safely():
    state = _make_state()
    attacker, defender = state.players
    _put_cauldron_in_play(attacker)
    state.supply["Curse"] = 0

    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))
    state.gain_card(attacker, get_card("Village"))

    # Trigger fired but no curses were available.
    assert attacker.cauldron_triggered
    assert not any(c.name == "Curse" for c in defender.discard)
