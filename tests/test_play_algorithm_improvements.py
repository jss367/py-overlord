"""Tests for play-algorithm improvements: hand-aware predicates and the smarter
unexpected-action fallback in :class:`EnhancedStrategy`.

The new predicates let strategies express synergy and over-commit checks that
the existing condition vocabulary couldn't capture (e.g. "play Village only if
a terminal is queued in hand", "don't play another Smithy if it would strand
my actions"). The fallback improvements pick the safest available unexpected
action — preferring cantrips over terminals — instead of the previous
"first non-terminal wins" rule.
"""

import types

from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _make_state():
    state = types.SimpleNamespace()
    state.turn_number = 1
    state.supply = {}
    state.empty_piles = 0
    state.players = []
    state.ways = []
    return state


def _make_player(hand=None, actions=1):
    player = types.SimpleNamespace()
    player.hand = list(hand or [])
    player.in_play = []
    player.actions = actions
    player.actions_gained_this_turn = 0
    player.cards_gained_this_turn = 0
    return player


# ----------------------------------------------------------------------
# Hand-aware predicates
# ----------------------------------------------------------------------

class TestCardInHand:
    def test_true_when_card_in_hand(self):
        cond = PriorityRule.card_in_hand("Smithy")
        player = _make_player(hand=[get_card("Smithy")])
        assert cond(_make_state(), player) is True

    def test_false_when_card_absent(self):
        cond = PriorityRule.card_in_hand("Smithy")
        player = _make_player(hand=[get_card("Village")])
        assert cond(_make_state(), player) is False

    def test_source_tagged(self):
        cond = PriorityRule.card_in_hand("Smithy")
        assert cond._source == "PriorityRule.card_in_hand('Smithy')"


class TestActionsInHand:
    def test_counts_action_cards(self):
        cond = PriorityRule.actions_in_hand(">=", 2)
        player = _make_player(hand=[get_card("Village"), get_card("Smithy"), get_card("Copper")])
        assert cond(_make_state(), player) is True

    def test_excludes_treasures_and_victories(self):
        cond = PriorityRule.actions_in_hand(">=", 1)
        player = _make_player(hand=[get_card("Copper"), get_card("Estate"), get_card("Silver")])
        assert cond(_make_state(), player) is False


class TestTerminalsInHand:
    def test_counts_terminal_actions_only(self):
        # Smithy is a terminal (+3 cards, 0 actions). Village is non-terminal.
        cond = PriorityRule.terminals_in_hand(">=", 1)
        player = _make_player(hand=[get_card("Smithy"), get_card("Village")])
        assert cond(_make_state(), player) is True

    def test_zero_when_only_non_terminals(self):
        cond = PriorityRule.terminals_in_hand(">=", 1)
        player = _make_player(hand=[get_card("Village"), get_card("Village")])
        assert cond(_make_state(), player) is False

    def test_threshold_arithmetic(self):
        cond_eq2 = PriorityRule.terminals_in_hand("==", 2)
        player = _make_player(hand=[get_card("Smithy"), get_card("Witch")])
        assert cond_eq2(_make_state(), player) is True


class TestTreasuresInHand:
    def test_counts_treasures(self):
        cond = PriorityRule.treasures_in_hand(">=", 2)
        player = _make_player(hand=[get_card("Copper"), get_card("Silver"), get_card("Estate")])
        assert cond(_make_state(), player) is True

    def test_excludes_actions(self):
        cond = PriorityRule.treasures_in_hand(">=", 1)
        player = _make_player(hand=[get_card("Smithy"), get_card("Village")])
        assert cond(_make_state(), player) is False


class TestExcessActions:
    def test_positive_when_actions_exceed_terminals(self):
        # 2 actions remaining, 1 terminal in hand → 1 action of headroom.
        cond = PriorityRule.excess_actions(">=", 1)
        player = _make_player(hand=[get_card("Smithy")], actions=2)
        assert cond(_make_state(), player) is True

    def test_zero_when_actions_equal_terminals(self):
        cond = PriorityRule.excess_actions(">=", 1)
        player = _make_player(hand=[get_card("Smithy")], actions=1)
        assert cond(_make_state(), player) is False

    def test_negative_when_terminals_exceed_actions(self):
        # 1 action, 2 terminals → -1 excess (over-committed).
        cond = PriorityRule.excess_actions("<", 0)
        player = _make_player(hand=[get_card("Smithy"), get_card("Witch")], actions=1)
        assert cond(_make_state(), player) is True

    def test_non_terminals_dont_count(self):
        # Village is non-terminal — playing it gives back the action. Excess should still match.
        cond = PriorityRule.excess_actions(">=", 1)
        player = _make_player(hand=[get_card("Village")], actions=1)
        assert cond(_make_state(), player) is True

    def test_source_tagged(self):
        cond = PriorityRule.excess_actions("<", 0)
        assert cond._source == "PriorityRule.excess_actions('<', 0)"


# ----------------------------------------------------------------------
# Smarter unexpected-action fallback
# ----------------------------------------------------------------------

class TestUnexpectedActionFallback:
    """`EnhancedStrategy.choose_action` falls back to a scored selection when the
    priority list returns no match. Cantrips beat plain non-terminals, and
    non-terminals beat terminals."""

    def test_prefers_cantrip_over_plain_non_terminal(self):
        # Laboratory (+2 cards +1 action) vs Necropolis-style? Use Lab vs Village.
        # Lab is a cantrip-and-then-some; Village is +1 card +2 actions. Both are
        # non-terminals. The fallback should still pick something reasonable —
        # specifically, a card that draws is preferred for tie-breaking.
        strategy = EnhancedStrategy()  # empty action_priority — everything is unexpected
        lab = get_card("Laboratory")
        village = get_card("Village")
        choice = strategy.choose_action(_make_state(), _make_player(), [lab, village])
        # Both are cantrips; tie-break by (cantrip, +actions, +cards). Village
        # wins on +actions (2 vs 1).
        assert choice is village

    def test_prefers_non_terminal_over_terminal(self):
        strategy = EnhancedStrategy()
        smithy = get_card("Smithy")          # terminal +3 cards
        village = get_card("Village")         # non-terminal +1 card +2 actions
        choice = strategy.choose_action(_make_state(), _make_player(), [smithy, village])
        assert choice is village

    def test_falls_back_to_best_terminal(self):
        # Only terminals — pick the one with most net cards.
        strategy = EnhancedStrategy()
        smithy = get_card("Smithy")           # +3 cards
        moat = get_card("Moat")               # +2 cards
        choice = strategy.choose_action(_make_state(), _make_player(), [moat, smithy])
        assert choice is smithy

    def test_returns_none_for_empty_choices(self):
        strategy = EnhancedStrategy()
        assert strategy.choose_action(_make_state(), _make_player(), []) is None

    def test_priority_list_still_takes_precedence(self):
        # When a priority rule matches, the fallback is not consulted.
        strategy = EnhancedStrategy()
        strategy.action_priority = [PriorityRule("Smithy")]
        smithy = get_card("Smithy")
        village = get_card("Village")
        choice = strategy.choose_action(_make_state(), _make_player(), [smithy, village])
        assert choice is smithy
