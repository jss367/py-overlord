"""Tests for Reserve / Duration inheritance via the Adventures Inheritance event.

Until now Reserve and Duration cards were explicitly excluded from
Inheritance because the engine could not soundly persist the inherited
overlay across the Tavern mat / Duration zone:
  * Reserve: the Estate ended up stuck on the Tavern mat with no
    ``on_call_from_tavern`` bound after the overlay was torn down.
  * Duration: the Estate sat in the duration zone with no
    ``on_duration`` bound, so the next-turn effect never fired.

These tests pin down the corrected behaviour for supported callbacks and
the guard that keeps unsupported callbacks out of the candidate list.
"""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState

from tests.utils import ChooseFirstActionAI


def _new_state(kingdom_card_names):
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card(n) for n in kingdom_card_names])
    return state


def test_inheritance_allows_reserve_card():
    """Supported Reserve cards in the $0-$4 band are eligible targets."""
    state = _new_state(["Guide"])
    candidates = get_event("Inheritance")._eligible_candidates(state)
    assert any(c.name == "Guide" for c in candidates)


def test_inheritance_allows_duration_card():
    """Supported Duration cards in the $0-$4 band are eligible targets."""
    state = _new_state(["Caravan"])
    candidates = get_event("Inheritance")._eligible_candidates(state)
    assert any(c.name == "Caravan" for c in candidates)


def test_inheritance_filters_unsupported_reserve_duration_cards():
    """Cards whose callbacks need unsupported Estate overlay state stay hidden."""
    state = _new_state([
        "Amulet",
        "Clerk",
        "Dungeon",
        "Garrison",
        "Grotto",
        "Guide",
        "Caravan",
    ])

    candidates = get_event("Inheritance")._eligible_candidates(state)
    candidate_names = {c.name for c in candidates}

    assert {"Guide", "Caravan"} <= candidate_names
    assert "Clerk" in candidate_names
    assert "Amulet" not in candidate_names
    assert "Dungeon" not in candidate_names
    assert "Garrison" not in candidate_names
    assert "Grotto" not in candidate_names


def test_inherited_caravan_fires_duration_effect_next_turn():
    """Playing an Estate as Caravan must place the Estate in the duration
    zone with the inherited on_duration bound; the next turn's duration
    phase fires +1 Card and moves the Estate to discard."""
    state = _new_state(["Caravan"])
    player = state.players[0]
    player.inherited_action_name = "Caravan"

    estate = get_card("Estate")
    player.hand = [estate]
    # Stock deck so both the play (+1 Card) and the next-turn duration
    # (+1 Card) have something to draw.
    player.deck = [get_card("Copper") for _ in range(6)]
    player.actions = 1

    state.current_player_index = 0
    state.phase = "action"
    state.handle_action_phase()

    # During the play: Estate moved from hand to duration; +1 Card drawn.
    assert estate in player.duration, (
        "Estate played as Caravan should land in the duration zone"
    )
    assert estate not in player.hand

    # Advance to the next turn and run the duration phase.
    state.handle_cleanup_phase()
    state.current_player_index = 0
    player.actions = 1
    hand_before = len(player.hand)
    state.phase = "duration"
    state.do_duration_phase()

    # The inherited Caravan duration effect draws +1 Card. Without that,
    # the Estate would silently leave duration (because Estate has no
    # ``duration_persistent`` attribute set) but the +1 Card never fires —
    # which is the original bug we're guarding against.
    assert len(player.hand) == hand_before + 1, (
        "Inherited Caravan must fire its on_duration +1 Card next turn"
    )
    assert estate not in player.duration


def test_inherited_guide_resolves_call_from_tavern():
    """Playing an Estate as Guide must place the Estate on the Tavern mat
    with the inherited on_call_from_tavern bound; at start of next turn
    the call fires (discard hand, draw 5) and the Estate moves to discard."""
    state = _new_state(["Guide"])
    player = state.players[0]
    player.inherited_action_name = "Guide"

    estate = get_card("Estate")
    player.hand = [estate]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.actions = 1

    state.current_player_index = 0
    state.phase = "action"
    state.handle_action_phase()

    # Estate landed on the Tavern mat (not in discard / not stuck in play).
    assert estate in player.tavern_mat
    assert estate not in player.in_play

    # Move to next turn; the start-of-turn tavern trigger should fire the
    # Guide call (discard hand, draw 5) and discard the Estate off the mat.
    state.handle_cleanup_phase()
    state.current_player_index = 0
    state.handle_start_phase()

    assert estate not in player.tavern_mat, (
        "Guide call must release the Estate from the Tavern mat"
    )
    assert estate in player.discard
    assert estate.name == "Estate", (
        "Overlay must be torn down after the call resolves"
    )


def test_inherited_estate_in_duration_counts_as_one_vp():
    """While the inheritance overlay is live (Estate sitting in duration
    zone), the Estate must still count as 1 VP — otherwise end-of-game
    scoring under-counts inherited Estates that haven't finished their
    Duration cycle."""
    state = _new_state(["Caravan"])
    player = state.players[0]
    player.inherited_action_name = "Caravan"

    estate = get_card("Estate")
    player.hand = [estate]
    player.deck = [get_card("Copper") for _ in range(2)]
    player.actions = 1

    state.current_player_index = 0
    state.phase = "action"
    state.handle_action_phase()

    assert estate in player.duration
    # While the overlay is live, the Estate is still a Victory card worth 1.
    assert estate.get_victory_points(player) == 1
