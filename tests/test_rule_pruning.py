"""Tests for empirical rule pruning.

These cover the profile-based pruning that complements the syntactic
``genome_simplification``. The priority walker records which rules
actually fire during play; rules that never fire across an evaluation
window are then dropped from the strategy so the GA's mutation budget
isn't spent on dead code.
"""

import types

from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.rule_pruning import (
    prune_unfired_rules,
    reset_fire_flags,
)
from dominion.strategy.strategies.base_strategy import BaseStrategy


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


def _strategy_with_gain(rules) -> EnhancedStrategy:
    s = BaseStrategy()
    s.gain_priority = list(rules)
    return s


# ----------------------------------------------------------------------
# Fire tracking on PriorityRule
# ----------------------------------------------------------------------


class TestFireTracking:
    def test_matching_rule_is_marked_fired(self):
        rule_silver = PriorityRule("Silver")
        rule_gold = PriorityRule("Gold")
        strategy = _strategy_with_gain([rule_gold, rule_silver])

        # Player can only afford Silver — Gold not in choices.
        chosen = strategy.choose_gain(
            _make_state(), _make_player(), [get_card("Silver")]
        )
        assert chosen.name == "Silver"
        assert getattr(rule_silver, "_fired", False) is True
        # Gold rule never matched anything in choices.
        assert getattr(rule_gold, "_fired", False) is False

    def test_unfired_rule_stays_false_after_no_choices(self):
        rule = PriorityRule("Province")
        strategy = _strategy_with_gain([rule])

        strategy.choose_gain(_make_state(), _make_player(), [get_card("Silver")])
        assert getattr(rule, "_fired", False) is False

    def test_only_first_matching_rule_fires(self):
        """Walker returns on the first match — later rules for the same card
        should remain unfired even when the card is in choices."""
        first = PriorityRule("Silver")
        second = PriorityRule("Silver")
        strategy = _strategy_with_gain([first, second])

        strategy.choose_gain(
            _make_state(), _make_player(), [get_card("Silver")]
        )
        assert getattr(first, "_fired", False) is True
        assert getattr(second, "_fired", False) is False

    def test_conditional_rule_with_failing_condition_does_not_fire(self):
        late_only = PriorityRule(
            "Silver", PriorityRule.turn_number(">=", 20)
        )
        fallback = PriorityRule("Silver")
        strategy = _strategy_with_gain([late_only, fallback])

        state = _make_state()
        state.turn_number = 3  # late_only condition fails
        strategy.choose_gain(state, _make_player(), [get_card("Silver")])

        assert getattr(late_only, "_fired", False) is False
        assert getattr(fallback, "_fired", False) is True

    def test_action_priority_also_tracked(self):
        rule = PriorityRule("Village")
        strategy = BaseStrategy()
        strategy.action_priority = [rule]

        # choose_action walks action_priority the same way.
        strategy.choose_action(
            _make_state(), _make_player(), [get_card("Village")]
        )
        assert getattr(rule, "_fired", False) is True


# ----------------------------------------------------------------------
# reset_fire_flags
# ----------------------------------------------------------------------


class TestResetFireFlags:
    def test_reset_clears_all_priority_lists(self):
        gain_rule = PriorityRule("Silver")
        gain_rule._fired = True
        action_rule = PriorityRule("Village")
        action_rule._fired = True
        treasure_rule = PriorityRule("Gold")
        treasure_rule._fired = True
        trash_rule = PriorityRule("Estate")
        trash_rule._fired = True

        strategy = BaseStrategy()
        strategy.gain_priority = [gain_rule]
        strategy.action_priority = [action_rule]
        strategy.treasure_priority = [treasure_rule]
        strategy.trash_priority = [trash_rule]

        reset_fire_flags(strategy)

        for r in (gain_rule, action_rule, treasure_rule, trash_rule):
            assert getattr(r, "_fired", False) is False


# ----------------------------------------------------------------------
# prune_unfired_rules
# ----------------------------------------------------------------------


class TestPruneUnfiredRules:
    def test_drops_only_unfired_rules(self):
        fired = PriorityRule("Silver")
        fired._fired = True
        unfired = PriorityRule("Gold")
        unfired._fired = False
        strategy = _strategy_with_gain([fired, unfired])

        prune_unfired_rules(strategy)

        assert [r.card for r in strategy.gain_priority] == ["Silver"]

    def test_preserves_order_of_remaining_rules(self):
        a = PriorityRule("Province"); a._fired = True
        b = PriorityRule("Gold"); b._fired = False
        c = PriorityRule("Silver"); c._fired = True
        d = PriorityRule("Copper"); d._fired = False
        e = PriorityRule("Estate"); e._fired = True
        strategy = _strategy_with_gain([a, b, c, d, e])

        prune_unfired_rules(strategy)

        assert [r.card for r in strategy.gain_priority] == [
            "Province", "Silver", "Estate"
        ]

    def test_respects_minimum_rules_floor(self):
        """When pruning would shrink a list below ``min_rules``, keep extra
        unfired rules in their original order to maintain the floor."""
        a = PriorityRule("Province"); a._fired = True
        b = PriorityRule("Gold"); b._fired = False
        c = PriorityRule("Silver"); c._fired = False
        strategy = _strategy_with_gain([a, b, c])

        prune_unfired_rules(strategy, min_rules=2)

        # First fired rule kept; one unfired kept to satisfy floor.
        assert [r.card for r in strategy.gain_priority] == ["Province", "Gold"]

    def test_no_op_when_all_rules_fired(self):
        a = PriorityRule("Silver"); a._fired = True
        b = PriorityRule("Gold"); b._fired = True
        strategy = _strategy_with_gain([a, b])

        prune_unfired_rules(strategy)

        assert [r.card for r in strategy.gain_priority] == ["Silver", "Gold"]

    def test_prunes_across_all_priority_lists(self):
        strategy = BaseStrategy()
        for attr in ("gain_priority", "action_priority",
                     "treasure_priority", "trash_priority"):
            fired = PriorityRule("Silver"); fired._fired = True
            unfired = PriorityRule("Gold")  # no _fired set
            setattr(strategy, attr, [fired, unfired])

        prune_unfired_rules(strategy)

        for attr in ("gain_priority", "action_priority",
                     "treasure_priority", "trash_priority"):
            cards = [r.card for r in getattr(strategy, attr)]
            assert cards == ["Silver"], f"{attr} not pruned: {cards}"

    def test_empty_priority_lists_unchanged(self):
        strategy = _strategy_with_gain([])
        prune_unfired_rules(strategy)
        assert strategy.gain_priority == []


# ----------------------------------------------------------------------
# Integration: profile + prune cycle
# ----------------------------------------------------------------------


class TestProfilePruneCycle:
    def test_profile_then_prune_removes_dominated_rule(self):
        """Realistic flow: a rule that's structurally reachable but always
        beaten by an earlier rule should get pruned after profiling."""
        early = PriorityRule("Silver")   # always wins at $3+
        dominated = PriorityRule("Copper")  # technically affordable but never preferred
        strategy = _strategy_with_gain([early, dominated])

        # Simulate 5 buy decisions where both Silver and Copper are affordable.
        for _ in range(5):
            strategy.choose_gain(
                _make_state(),
                _make_player(),
                [get_card("Silver"), get_card("Copper")],
            )

        prune_unfired_rules(strategy)
        assert [r.card for r in strategy.gain_priority] == ["Silver"]

    def test_reset_makes_profile_window_fresh(self):
        """After reset_fire_flags, a subsequent eval window measures only
        new fires — old fires shouldn't keep stale rules alive."""
        a = PriorityRule("Silver")
        b = PriorityRule("Copper")
        strategy = _strategy_with_gain([a, b])

        # Window 1: both fire (Silver first; Copper alone next).
        strategy.choose_gain(
            _make_state(), _make_player(), [get_card("Silver")]
        )
        strategy.choose_gain(
            _make_state(), _make_player(), [get_card("Copper")]
        )
        assert getattr(a, "_fired") and getattr(b, "_fired")

        reset_fire_flags(strategy)
        # Window 2: only Silver fires.
        strategy.choose_gain(
            _make_state(), _make_player(), [get_card("Silver")]
        )

        prune_unfired_rules(strategy)
        assert [r.card for r in strategy.gain_priority] == ["Silver"]
