"""Regression tests for Adventures bug fixes (post PR #189)."""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState

from tests.utils import ChooseFirstActionAI


def _new_state(kingdom_card_names, players=1):
    ais = [ChooseFirstActionAI() for _ in range(players)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card(n) for n in kingdom_card_names])
    for p in state.players:
        p.hand = []
        p.deck = []
        p.discard = []
    return state


# ----------------------------------------------------------------------
# P1: Teacher must leave the Tavern mat when called
# ----------------------------------------------------------------------

def test_teacher_leaves_tavern_when_called():
    """Teacher is a Reserve card; calling it discards it. The same Teacher
    cannot be called repeatedly across turns to stack token placements."""
    state = _new_state(["Smithy", "Village"])
    p = state.players[0]
    from dominion.cards.adventures.peasant import Teacher
    teacher = Teacher()
    p.tavern_mat.append(teacher)

    state._call_tavern_triggers(p, "start_of_turn")
    assert teacher in p.discard, "Teacher must move to discard when called"
    assert teacher not in p.tavern_mat
    placed = sum(
        1 for tokens in state.pile_tokens.values() for t in tokens
        if t in {"+1 Card", "+1 Action", "+1 Buy", "+$1"}
    )
    assert placed == 1, "exactly one token placed per Teacher call"


def test_teacher_cannot_place_two_tokens_across_turns():
    """A single Teacher copy cannot stack token placements across turns."""
    state = _new_state(["Smithy", "Village"])
    p = state.players[0]
    from dominion.cards.adventures.peasant import Teacher
    teacher = Teacher()
    p.tavern_mat.append(teacher)

    # Call once.
    state._call_tavern_triggers(p, "start_of_turn")
    assert teacher in p.discard

    # If Teacher were still on the mat, a second start-of-turn trigger could
    # place a second token. After the fix the mat is empty.
    p.tavern_mat = [c for c in p.tavern_mat if c is not teacher]
    state._call_tavern_triggers(p, "start_of_turn")
    placed = sum(
        1 for tokens in state.pile_tokens.values() for t in tokens
        if t in {"+1 Card", "+1 Action", "+1 Buy", "+$1"}
    )
    assert placed == 1, "second turn must not place another token"


# ----------------------------------------------------------------------
# P1: Inheritance must skip Reserve / Duration candidates
# ----------------------------------------------------------------------

def test_inheritance_skips_reserve_candidates():
    state = _new_state(["Guide", "Ratcatcher"])
    p = state.players[0]
    inh = get_event("Inheritance")
    inh.on_buy(state, p)
    # Both candidates are Reserve → none eligible → nothing inherited.
    assert p.inherited_action_name is None


def test_inheritance_skips_duration_candidates():
    state = _new_state(["Gear", "Hireling"])
    p = state.players[0]
    inh = get_event("Inheritance")
    inh.on_buy(state, p)
    # Gear is Duration ($3); Hireling is Duration ($6 — also out of range).
    assert p.inherited_action_name is None


def test_inheritance_picks_eligible_action_when_both_present():
    state = _new_state(["Guide", "Smithy"])
    p = state.players[0]
    inh = get_event("Inheritance")
    inh.on_buy(state, p)
    # Smithy is the only non-Reserve/non-Duration eligible Action.
    assert p.inherited_action_name == "Smithy"


# ----------------------------------------------------------------------
# P2: Dungeon enforces the mandatory second discard
# ----------------------------------------------------------------------

def test_dungeon_forces_second_discard_when_ai_under_selects():
    """If the AI returns fewer than 2 discards, Dungeon must still discard
    two cards from hand (the card text mandates it)."""
    state = _new_state(["Dungeon"])
    p = state.players[0]

    class StubAI(ChooseFirstActionAI):
        # Override choose_cards_to_discard to return nothing.
        def choose_cards_to_discard(self, *_args, **_kwargs):
            return []

    p.ai = StubAI()
    p.hand = [get_card("Copper"), get_card("Estate"), get_card("Silver")]
    p.deck = []  # so Dungeon's draw 2 is a no-op

    dungeon = get_card("Dungeon")
    dungeon._draw_then_discard_two(state, p)

    # Started 3, drew 0, must discard 2 → hand size 1.
    assert len(p.hand) == 1, "Dungeon must force the mandatory second discard"
    assert len(p.discard) == 2


# ----------------------------------------------------------------------
# P2: Inheritance overlay propagates inherited types to downstream hooks
# ----------------------------------------------------------------------

def test_inheritance_estate_seen_as_inherited_type_for_training_token():
    """An Estate played under Inheritance(Smithy) with a training token on
    Smithy should grant the +$1 training bonus, because the played card is
    treated as a Smithy for type/name-gated downstream hooks."""
    state = _new_state(["Smithy"])
    p = state.players[0]
    p.inherited_action_name = "Smithy"
    p.training_pile = "Smithy"
    p.hand = [get_card("Estate")]
    p.deck = [get_card("Copper") for _ in range(5)]
    p.actions = 1
    p.coins = 0
    state.phase = "action"
    state.handle_action_phase()
    # Smithy gives +3 Cards (no +$); the training token contributes the +$1.
    assert p.coins == 1, (
        "Estate-as-Smithy must trigger the training-token bonus on Smithy"
    )
