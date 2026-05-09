"""Tests for the evolvable ``way_policy`` mechanism.

The Way of the Butterfly trick used to be hardcoded for Trail only. With
``way_policy``, evolved strategies can declare per-card Way usage so the
genetic evolver can discover, e.g., butterflying Flag Bearer on the
Victoria board.
"""

from __future__ import annotations

import importlib
import sys
import types

from dominion.boards.loader import BoardConfig
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
    WayRule,
)
from dominion.strategy.genome_simplification import simplify_strategy
from dominion.strategy.strategies.base_strategy import BaseStrategy


def _mock_state():
    state = types.SimpleNamespace()
    state.supply = {}
    state.turn_number = 1
    state.empty_piles = 0
    state.players = []
    state.ways = []
    return state


def _mock_player():
    player = types.SimpleNamespace()
    player.coins = 0
    player.actions = 1
    player.buys = 1
    player.hand = []
    player.in_play = []
    player.count_in_deck = lambda _name: 0
    player.all_cards = lambda: []
    player.get_victory_points = lambda *_: 0
    return player


class _StubWay:
    def __init__(self, name: str):
        self.name = name


class _StubCard:
    def __init__(self, name: str, cost_coins: int = 4):
        self.name = name
        self.cost = types.SimpleNamespace(coins=cost_coins, potions=0)


class TestChooseWayPolicy:
    """way_policy fires before the hardcoded Trail fallback."""

    def test_unconditional_rule_returns_matching_way(self):
        strategy = EnhancedStrategy()
        strategy.way_policy = [WayRule("Flag Bearer", "Way of the Butterfly")]

        butterfly = _StubWay("Way of the Butterfly")
        chosen = strategy.choose_way(
            _mock_state(), _mock_player(), _StubCard("Flag Bearer"), [butterfly, None]
        )
        assert chosen is butterfly

    def test_card_name_must_match(self):
        strategy = EnhancedStrategy()
        strategy.way_policy = [WayRule("Flag Bearer", "Way of the Butterfly")]

        butterfly = _StubWay("Way of the Butterfly")
        chosen = strategy.choose_way(
            _mock_state(), _mock_player(), _StubCard("Smithy"), [butterfly, None]
        )
        assert chosen is None

    def test_way_must_be_in_offered_list(self):
        strategy = EnhancedStrategy()
        strategy.way_policy = [WayRule("Flag Bearer", "Way of the Mouse")]

        butterfly = _StubWay("Way of the Butterfly")
        chosen = strategy.choose_way(
            _mock_state(), _mock_player(), _StubCard("Flag Bearer"), [butterfly, None]
        )
        assert chosen is None

    def test_condition_gates_the_rule(self):
        strategy = EnhancedStrategy()
        strategy.way_policy = [
            WayRule(
                "Flag Bearer",
                "Way of the Butterfly",
                PriorityRule.turn_number(">=", 100),  # never fires this early
            )
        ]
        butterfly = _StubWay("Way of the Butterfly")
        chosen = strategy.choose_way(
            _mock_state(), _mock_player(), _StubCard("Flag Bearer"), [butterfly, None]
        )
        assert chosen is None

    def test_first_matching_rule_wins(self):
        """Earlier rules in the list should beat later ones for the same card."""
        strategy = EnhancedStrategy()
        mouse = _StubWay("Way of the Mouse")
        butterfly = _StubWay("Way of the Butterfly")
        strategy.way_policy = [
            WayRule("Flag Bearer", "Way of the Mouse"),
            WayRule("Flag Bearer", "Way of the Butterfly"),
        ]

        chosen = strategy.choose_way(
            _mock_state(),
            _mock_player(),
            _StubCard("Flag Bearer"),
            [mouse, butterfly, None],
        )
        assert chosen is mouse

    def test_falls_back_to_trail_default_when_no_rule_matches(self):
        """Empty (or non-matching) way_policy still triggers the Trail fallback."""
        strategy = EnhancedStrategy()
        strategy.gain_priority = [PriorityRule("Smithy")]
        # way_policy is empty by default

        state = _mock_state()
        state.supply = {"Smithy": 5}
        state.ways = [_StubWay("Way of the Butterfly")]

        # Patch _best_butterfly_target to avoid pulling in the real card registry.
        strategy._best_butterfly_target = lambda *_: "Smithy"

        butterfly = _StubWay("Way of the Butterfly")
        chosen = strategy.choose_way(
            state, _mock_player(), _StubCard("Trail", cost_coins=4), [butterfly, None]
        )
        assert chosen is butterfly


class TestSimplification:
    def test_simplify_dedupes_way_rules(self):
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province")]
        s.way_policy = [
            WayRule("Flag Bearer", "Way of the Butterfly"),
            WayRule("Flag Bearer", "Way of the Butterfly"),  # dropped
            WayRule("Sailor", "Way of the Butterfly"),
        ]
        simplified = simplify_strategy(s)
        cards = [(r.card_name, r.way_name) for r in simplified.way_policy]
        assert cards == [
            ("Flag Bearer", "Way of the Butterfly"),
            ("Sailor", "Way of the Butterfly"),
        ]

    def test_unconditional_dominates_later_rules_for_same_pair(self):
        s = BaseStrategy()
        s.way_policy = [
            WayRule("Flag Bearer", "Way of the Butterfly"),  # unconditional
            WayRule(
                "Flag Bearer",
                "Way of the Butterfly",
                PriorityRule.turn_number("<=", 5),
            ),  # dropped — unreachable
            # Different (card, way) pair survives.
            WayRule("Flag Bearer", "Way of the Mouse"),
        ]
        simplified = simplify_strategy(s)
        sigs = [(r.card_name, r.way_name, r.condition) for r in simplified.way_policy]
        assert sigs == [
            ("Flag Bearer", "Way of the Butterfly", None),
            ("Flag Bearer", "Way of the Mouse", None),
        ]


class TestMutation:
    """The genetic trainer should mutate way_policy when a board has Ways."""

    def _victoria_trainer(self) -> GeneticTrainer:
        board = BoardConfig(
            kingdom_cards=["Flag Bearer", "Sailor", "Treasury", "Charlatan"],
            ways=["Way of the Butterfly"],
        )
        return GeneticTrainer(
            kingdom_cards=board.kingdom_cards,
            population_size=2,
            generations=1,
            games_per_eval=1,
            board_config=board,
        )

    def test_random_way_rule_targets_kingdom_action_and_board_way(self):
        trainer = self._victoria_trainer()
        # Force determinism via a long sample loop.
        for _ in range(20):
            rule = trainer._random_way_rule()
            assert rule is not None
            assert rule.card_name in trainer._kingdom_action_cards
            assert rule.way_name == "Way of the Butterfly"
            assert rule.condition is None or callable(rule.condition)

    def test_no_ways_yields_no_random_rule(self):
        trainer = GeneticTrainer(
            kingdom_cards=["Village", "Smithy"],
            population_size=1,
            generations=1,
            games_per_eval=1,
        )
        assert trainer._random_way_rule() is None

    def test_mutation_grows_way_policy_over_iterations(self):
        """Repeated mutation should eventually produce a non-empty way_policy."""
        trainer = self._victoria_trainer()
        trainer.mutation_rate = 0.9  # crank way up so the test isn't flaky

        strategy = BaseStrategy()
        strategy.way_policy = []
        # Seed gain/treasure so _mutate runs cleanly.
        strategy.gain_priority = [PriorityRule("Province")]
        strategy.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        for _ in range(50):
            trainer._mutate(strategy)
            if strategy.way_policy:
                break

        assert strategy.way_policy, "way_policy should grow after many mutations"
        for rule in strategy.way_policy:
            assert rule.way_name == "Way of the Butterfly"
            assert rule.card_name in trainer._kingdom_action_cards


class TestSerializationRoundTrip:
    def test_strategy_with_way_policy_round_trips(self, tmp_path):
        from runner import save_strategy_as_python

        strategy = BaseStrategy()
        strategy.name = "VictoriaButterfly"
        strategy.gain_priority = [PriorityRule("Province")]
        strategy.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]
        strategy.way_policy = [
            WayRule("Flag Bearer", "Way of the Butterfly"),
            WayRule(
                "Sailor",
                "Way of the Butterfly",
                PriorityRule.turn_number("<=", 8),
            ),
        ]

        out_file = tmp_path / "victoria_butterfly_strategy.py"
        save_strategy_as_python(strategy, out_file, "VictoriaButterflyStrategy")

        source = out_file.read_text()
        assert "WayRule" in source, "way_policy should be emitted"
        assert "Way of the Butterfly" in source
        assert "<lambda" not in source
        assert "<function" not in source

        sys.path.insert(0, str(tmp_path))
        try:
            mod = importlib.import_module("victoria_butterfly_strategy")
            generated = mod.VictoriaButterflyStrategy()
            assert generated.name == "VictoriaButterfly"
            assert len(generated.way_policy) == 2
            first, second = generated.way_policy
            assert first.card_name == "Flag Bearer"
            assert first.way_name == "Way of the Butterfly"
            assert first.condition is None
            assert second.card_name == "Sailor"
            assert callable(second.condition)
        finally:
            sys.path.pop(0)
            sys.modules.pop("victoria_butterfly_strategy", None)

    def test_strategy_without_way_policy_omits_wayrule_import(self, tmp_path):
        """No way_policy → keep the generated file lean (no WayRule import)."""
        from runner import save_strategy_as_python

        strategy = BaseStrategy()
        strategy.name = "Plain"
        strategy.gain_priority = [PriorityRule("Province")]
        strategy.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        out_file = tmp_path / "plain_strategy.py"
        save_strategy_as_python(strategy, out_file, "PlainStrategy")
        source = out_file.read_text()

        assert "WayRule" not in source
