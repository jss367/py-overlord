"""Tests for evolvable Way selection (issue #231).

Covers:
- ``EnhancedStrategy.choose_way`` consults ``way_policy`` and respects
  conditions, card matching, and Way availability.
- ``GeneticTrainer`` seeds and mutates ``way_policy`` only when the board
  declares Ways.
- Genome simplification deduplicates ``way_policy`` and applies
  ``(card_name, way_name)``-scoped unconditional dominance without
  collapsing alternatives that target a different Way.
- Round-tripping a strategy through ``runner.save_strategy_as_python``
  preserves ``way_policy``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from dominion.boards.loader import BoardConfig
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
    WayRule,
)
from dominion.strategy.genome_simplification import simplify_strategy
from dominion.strategy.strategies.base_strategy import BaseStrategy
from dominion.ways.butterfly import WayOfTheButterfly
from dominion.ways.mole import WayOfTheMole

import runner


# ---------------------------------------------------------------------------
# choose_way honors way_policy
# ---------------------------------------------------------------------------


def _played_card(name: str, coins: int = 4) -> SimpleNamespace:
    cost = SimpleNamespace(coins=coins)
    return SimpleNamespace(name=name, cost=cost)


class TestChooseWayHonorsPolicy:
    def test_unconditional_rule_picks_named_way(self):
        strategy = EnhancedStrategy()
        strategy.way_policy = [WayRule("Flag Bearer", "Way of the Butterfly")]
        ways = [WayOfTheButterfly(), WayOfTheMole(), None]

        chosen = strategy.choose_way(
            state=None, player=None, card=_played_card("Flag Bearer"), ways=ways
        )
        assert chosen is not None and chosen.name == "Way of the Butterfly"

    def test_returns_none_when_card_doesnt_match(self):
        strategy = EnhancedStrategy()
        strategy.way_policy = [WayRule("Flag Bearer", "Way of the Butterfly")]
        chosen = strategy.choose_way(
            state=None,
            player=None,
            card=_played_card("Village"),
            ways=[WayOfTheButterfly(), None],
        )
        assert chosen is None

    def test_skips_rule_when_named_way_unavailable(self):
        strategy = EnhancedStrategy()
        strategy.way_policy = [
            WayRule("Flag Bearer", "Way of the Butterfly"),
            WayRule("Flag Bearer", "Way of the Mole"),
        ]
        # Butterfly not in this kingdom — should fall through to Mole rule.
        ways = [WayOfTheMole(), None]
        chosen = strategy.choose_way(
            state=None, player=None, card=_played_card("Flag Bearer"), ways=ways
        )
        assert chosen is not None and chosen.name == "Way of the Mole"

    def test_condition_gating_blocks_then_allows(self):
        strategy = EnhancedStrategy()
        # Condition takes (state, player); use a state-driven flag.
        cond = lambda s, _p: bool(s.allow_butterfly)
        strategy.way_policy = [WayRule("Flag Bearer", "Way of the Butterfly", cond)]
        ways = [WayOfTheButterfly(), None]
        card = _played_card("Flag Bearer")

        blocked_state = SimpleNamespace(allow_butterfly=False)
        assert strategy.choose_way(blocked_state, None, card, ways) is None

        allowed_state = SimpleNamespace(allow_butterfly=True)
        chosen = strategy.choose_way(allowed_state, None, card, ways)
        assert chosen is not None and chosen.name == "Way of the Butterfly"

    def test_default_trail_butterfly_when_policy_empty(self):
        """With no way_policy, Trail must still default to Way of the
        Butterfly when a viable $5 gain-priority target exists. The
        Trail-bias logic in choose_action/choose_gain depends on the Way
        picker agreeing."""
        strategy = EnhancedStrategy()
        # Stub the target lookup so we don't need a full gain_priority/supply.
        strategy._best_butterfly_target = lambda *_: "Smithy"

        ways = [WayOfTheButterfly(), None]
        chosen = strategy.choose_way(
            state=None, player=None, card=_played_card("Trail"), ways=ways
        )
        assert chosen is not None and chosen.name == "Way of the Butterfly"


# ---------------------------------------------------------------------------
# Genome simplification
# ---------------------------------------------------------------------------


class TestSimplifyWayPolicy:
    def _make(self, way_policy):
        s = BaseStrategy()
        s.way_policy = list(way_policy)
        return s

    def test_dedupes_identical_rules(self):
        cond = PriorityRule.turn_number("<=", 8)
        s = self._make(
            [
                WayRule("Flag Bearer", "Way of the Butterfly", cond),
                WayRule(
                    "Flag Bearer",
                    "Way of the Butterfly",
                    PriorityRule.turn_number("<=", 8),
                ),
            ]
        )
        out = simplify_strategy(s)
        assert len(out.way_policy) == 1

    def test_unconditional_dominates_same_card_and_way(self):
        s = self._make(
            [
                WayRule("Flag Bearer", "Way of the Butterfly"),
                WayRule(
                    "Flag Bearer",
                    "Way of the Butterfly",
                    PriorityRule.turn_number("<=", 5),
                ),
            ]
        )
        out = simplify_strategy(s)
        assert len(out.way_policy) == 1
        assert out.way_policy[0].condition is None

    def test_unconditional_does_not_dominate_different_way(self):
        # Different Ways for the same card represent different choices —
        # the second rule may fire if the first Way isn't in the kingdom.
        s = self._make(
            [
                WayRule("Flag Bearer", "Way of the Butterfly"),
                WayRule("Flag Bearer", "Way of the Mole"),
            ]
        )
        out = simplify_strategy(s)
        assert len(out.way_policy) == 2


# ---------------------------------------------------------------------------
# Genetic trainer integration
# ---------------------------------------------------------------------------


class TestGeneticTrainerWayPolicy:
    def test_no_way_policy_when_board_has_no_ways(self):
        trainer = GeneticTrainer(
            kingdom_cards=["Village", "Smithy", "Witch"],
            population_size=1,
            generations=1,
        )
        strategy = trainer.create_random_strategy()
        assert strategy.way_policy == []

    def test_seeds_way_policy_when_board_has_ways(self):
        # Seed RNG via repeated trials; with 0..2 random rules per strategy
        # we just need to see a nonempty list among many tries.
        board = BoardConfig(
            kingdom_cards=["Flag Bearer", "Village", "Smithy"],
            ways=["Way of the Butterfly", "Way of the Mole"],
        )
        trainer = GeneticTrainer(
            kingdom_cards=board.kingdom_cards,
            population_size=1,
            generations=1,
            board_config=board,
        )
        # Try many strategies — at least one should seed a way_policy rule.
        seeded = any(
            trainer.create_random_strategy().way_policy for _ in range(50)
        )
        assert seeded, "expected create_random_strategy to occasionally seed way_policy"

    def test_random_way_rule_returns_none_without_ways(self):
        trainer = GeneticTrainer(
            kingdom_cards=["Village"],
            population_size=1,
            generations=1,
        )
        assert trainer._random_way_rule() is None

    def test_random_way_rule_uses_kingdom_ways_only(self):
        board = BoardConfig(
            kingdom_cards=["Flag Bearer", "Village"],
            ways=["Way of the Butterfly"],
        )
        trainer = GeneticTrainer(
            kingdom_cards=board.kingdom_cards,
            population_size=1,
            generations=1,
            board_config=board,
        )
        for _ in range(20):
            rule = trainer._random_way_rule()
            assert rule is not None
            assert rule.way_name == "Way of the Butterfly"
            assert rule.card_name in trainer._kingdom_action_cards

    def test_parametric_mouse_way_is_canonicalized(self):
        """Boards declared as ``Way of the Mouse (Native Village)`` round-trip
        through ``WayRule.way_name`` as the unparameterised ``Way of the Mouse``
        — so the rule actually matches the runtime ``Way.name`` and isn't
        silently unreachable."""
        from dominion.ways.registry import get_way

        board = BoardConfig(
            kingdom_cards=["Flag Bearer", "Village"],
            ways=["Way of the Mouse (Native Village)"],
        )
        trainer = GeneticTrainer(
            kingdom_cards=board.kingdom_cards,
            population_size=1,
            generations=1,
            board_config=board,
        )
        assert trainer._kingdom_ways == ["Way of the Mouse"]

        # The runtime Way object also has the unparameterised name, so the
        # equality check in ``EnhancedStrategy._choose_from_way_policy``
        # succeeds.
        runtime_way = get_way("Way of the Mouse (Native Village)")
        assert runtime_way.name == trainer._kingdom_ways[0]


# ---------------------------------------------------------------------------
# Round-trip serialization
# ---------------------------------------------------------------------------


class TestRoundTripSerialization:
    def test_way_policy_serializes_and_reloads(self, tmp_path: Path):
        strategy = BaseStrategy()
        strategy.name = "RoundTrip"
        strategy.gain_priority = [PriorityRule("Province")]
        strategy.treasure_priority = [PriorityRule("Gold")]
        strategy.way_policy = [
            WayRule("Flag Bearer", "Way of the Butterfly"),
            WayRule(
                "Village",
                "Way of the Mole",
                PriorityRule.turn_number("<=", 5),
            ),
        ]

        path = tmp_path / "round_trip_strategy.py"
        runner.save_strategy_as_python(strategy, path, class_name="RoundTrip")

        # Import the generated module fresh and instantiate.
        spec = importlib.util.spec_from_file_location("round_trip_strategy", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules["round_trip_strategy"] = module
        try:
            spec.loader.exec_module(module)
            reloaded = module.RoundTrip()
        finally:
            sys.modules.pop("round_trip_strategy", None)

        assert len(reloaded.way_policy) == 2
        first, second = reloaded.way_policy
        assert (first.card_name, first.way_name, first.condition) == (
            "Flag Bearer",
            "Way of the Butterfly",
            None,
        )
        assert (second.card_name, second.way_name) == ("Village", "Way of the Mole")
        assert second.condition is not None
        # The reloaded condition should evaluate the same way as a fresh one.
        state = SimpleNamespace(turn_number=3)
        assert second.condition(state, None) is True
        late_state = SimpleNamespace(turn_number=10)
        assert second.condition(late_state, None) is False

    def test_serialized_file_omits_way_rule_import_when_empty(self, tmp_path: Path):
        strategy = BaseStrategy()
        strategy.name = "NoWays"
        strategy.gain_priority = [PriorityRule("Province")]
        path = tmp_path / "no_ways_strategy.py"
        runner.save_strategy_as_python(strategy, path, class_name="NoWays")
        text = path.read_text()
        assert "WayRule" not in text
