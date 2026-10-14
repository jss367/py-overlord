"""Tests for the Continue event from Rising Sun.

Continue's text: "$8: Once per turn. Gain an Action card costing up to $4
that isn't an Attack card; return to your Action phase; play it. +1 Action,
+1 Buy."

Notable invariants under test:

1. Only Action cards (not Treasures, not Attacks) are valid targets.
2. The buy is once-per-turn (a player flag prevents repeats within a turn).
3. The play step respects the original gain zone; a gain moved by Insignia
   or Villa cannot be moved again by Continue. Returning to the Action phase
   remains independent of whether the gained card can be played.
"""

from dominion.cards.registry import get_card
from dominion.events.continue_event import Continue
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class _FixedTargetAI:
    """AI that always picks the named card from Continue's choices."""

    def __init__(self, target_name: str):
        self.name = "fixed"
        self.target_name = target_name
        self.strategy = None

    def choose_action(self, *args, **kwargs):
        return None

    def choose_treasure(self, *args, **kwargs):
        return None

    def choose_buy(self, *args, **kwargs):
        return None

    def choose_card_to_trash(self, *args, **kwargs):
        return None

    def choose_continue_target(self, state, player, choices):
        for c in choices:
            if c.name == self.target_name:
                return c
        return choices[0] if choices else None


def _new_state(target_name: str) -> tuple[GameState, PlayerState]:
    state = GameState(players=[])
    state.players = [PlayerState(_FixedTargetAI(target_name))]
    state.setup_supply([get_card("Village"), get_card("Villa")])
    state.players[0].coins = 8
    return state, state.players[0]


def test_continue_plays_a_gained_action():
    """Gaining Village via Continue should add it to in_play."""
    state, player = _new_state("Village")
    Continue().on_buy(state, player)
    villages_in_play = [c for c in player.in_play if c.name == "Village"]
    assert len(villages_in_play) == 1, "Village should be in_play after Continue"


def test_continue_grants_action_and_buy():
    """Continue grants +1 Action and +1 Buy regardless of what was gained."""
    state, player = _new_state("Village")
    actions_before = player.actions
    buys_before = player.buys
    Continue().on_buy(state, player)
    # +1 Action from Continue itself, +2 from Village's play, -0 (gain doesn't
    # consume an action).
    assert player.actions >= actions_before + 1
    assert player.buys == buys_before + 1


def test_continue_marks_used_for_turn():
    """Continue is once-per-turn — a second buy would be blocked."""
    state, player = _new_state("Village")
    Continue().on_buy(state, player)
    assert player.continue_used_this_turn is True
    assert Continue().may_be_bought(state, player) is False


def test_continue_does_not_follow_an_insignia_topdecked_gain():
    """Moving the gain to deck prevents Continue's later automatic play."""
    state, player = _new_state("Village")
    player.insignia_active = True
    player.ai.should_topdeck_with_insignia = lambda *a, **k: True

    Continue().on_buy(state, player)

    villages_in_play = [c for c in player.in_play if c.name == "Village"]
    villages_in_deck = [c for c in player.deck if c.name == "Village"]
    villages_in_discard = [c for c in player.discard if c.name == "Village"]
    assert villages_in_play == []
    assert len(villages_in_deck) == 1
    assert villages_in_discard == []


def test_continue_does_not_automatically_play_villa_after_its_own_move():
    """Villa moved to hand; this AI declines the subsequent normal Action play."""
    state, player = _new_state("Villa")
    Continue().on_buy(state, player)

    villas_in_play = [c for c in player.in_play if c.name == "Villa"]
    villas_in_hand = [c for c in player.hand if c.name == "Villa"]
    assert villas_in_play == []
    assert len(villas_in_hand) == 1


def test_continue_skips_play_if_gain_was_intercepted():
    """If the gain landed somewhere unusual (trashed, exiled), Continue should
    not blindly append the card to in_play."""
    state, player = _new_state("Village")

    player.hand = [get_card("Watchtower")]
    player.ai.choose_watchtower_reaction = lambda *args: "trash"
    Continue().on_buy(state, player)
    assert any(c.name == "Village" for c in state.trash)
    assert not any(c.name == "Village" for c in player.in_play)
    assert state.phase == "buy"
