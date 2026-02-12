import importlib
import types
from pathlib import Path

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


def make_stub_strategy() -> BaseStrategy:
    strategy = BaseStrategy()
    strategy.name = "Stub"
    strategy.gain_priority = [PriorityRule("Province")]
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]
    return strategy


def test_evaluate_strategy_counts_second_seat_wins(monkeypatch):
    trainer = GeneticTrainer(["Village"], population_size=1, generations=1, games_per_eval=2)

    # Provide a deterministic strategy under test
    strategy = make_stub_strategy()

    call_counter = types.SimpleNamespace(count=0)

    def fake_run_game(first_ai, second_ai, kingdom):
        call_counter.count += 1
        # Big Money (second_ai in the first call) wins when our strategy leads.
        # Our strategy (second_ai in the second call) wins when going second.
        return second_ai, {}, None, 0

    monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)

    win_rate = trainer.evaluate_strategy(strategy)

    assert call_counter.count == 2
    assert win_rate == 50.0


# ---------------------------------------------------------------------------
# New tests: condition generation, evaluation, and serialization
# ---------------------------------------------------------------------------


def _make_mock_state(turn_number=5, provinces_left=8):
    """Create a lightweight mock GameState."""
    state = types.SimpleNamespace()
    state.turn_number = turn_number
    state.supply = {"Province": provinces_left}
    return state


def _make_mock_player(coins=3, actions=1, buys=1):
    """Create a lightweight mock PlayerState."""
    player = types.SimpleNamespace()
    player.coins = coins
    player.actions = actions
    player.buys = buys
    player.hand = []
    player.count_in_deck = lambda card_name: {"Silver": 2, "Gold": 1}.get(card_name, 0)
    return player


class TestConditionsAreCallable:
    """Verify that create_random_strategy produces callable (not string) conditions."""

    def test_gain_conditions_are_callable_or_none(self):
        trainer = GeneticTrainer(["Village", "Smithy"], population_size=1, generations=1)
        strategy = trainer.create_random_strategy()

        for rule in strategy.gain_priority:
            assert rule.condition is None or callable(rule.condition), (
                f"Gain condition for {rule.card_name} is {type(rule.condition)}, expected callable or None"
            )

    def test_action_conditions_are_callable_or_none(self):
        trainer = GeneticTrainer(["Village", "Smithy", "Laboratory"], population_size=1, generations=1)
        strategy = trainer.create_random_strategy()

        for rule in strategy.action_priority:
            assert rule.condition is None or callable(rule.condition), (
                f"Action condition for {rule.card_name} is {type(rule.condition)}, expected callable or None"
            )

    def test_trash_conditions_are_callable_or_none(self):
        trainer = GeneticTrainer(["Village"], population_size=1, generations=1)
        strategy = trainer.create_random_strategy()

        for rule in strategy.trash_priority:
            assert rule.condition is None or callable(rule.condition), (
                f"Trash condition for {rule.card_name} is {type(rule.condition)}, expected callable or None"
            )


class TestConditionsEvaluate:
    """Verify that conditions actually produce boolean results when called."""

    def test_provinces_left(self):
        cond = PriorityRule.provinces_left("<=", 4)
        state = _make_mock_state(provinces_left=3)
        player = _make_mock_player()
        assert cond(state, player) is True

        state2 = _make_mock_state(provinces_left=6)
        assert cond(state2, player) is False

    def test_turn_number(self):
        cond = PriorityRule.turn_number(">=", 5)
        assert cond(_make_mock_state(turn_number=5), _make_mock_player()) is True
        assert cond(_make_mock_state(turn_number=3), _make_mock_player()) is False

    def test_resources(self):
        cond = PriorityRule.resources("coins", ">=", 6)
        assert cond(_make_mock_state(), _make_mock_player(coins=8)) is True
        assert cond(_make_mock_state(), _make_mock_player(coins=3)) is False

    def test_has_cards(self):
        cond = PriorityRule.has_cards(["Silver", "Gold"], 3)
        player = _make_mock_player()  # Silver=2, Gold=1 → total 3
        assert cond(_make_mock_state(), player) is True

        cond2 = PriorityRule.has_cards(["Silver", "Gold"], 5)
        assert cond2(_make_mock_state(), player) is False

    def test_random_strategy_conditions_evaluate(self):
        """Every callable condition on a random strategy should evaluate without error."""
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Laboratory"],
            population_size=1, generations=1,
        )
        strategy = trainer.create_random_strategy()
        state = _make_mock_state()
        player = _make_mock_player()

        for rule_list in [strategy.gain_priority, strategy.action_priority, strategy.trash_priority]:
            for rule in rule_list:
                if rule.condition is not None:
                    result = rule.condition(state, player)
                    assert isinstance(result, bool), (
                        f"Condition for {rule.card_name} returned {type(result)}, expected bool"
                    )


class TestSourceAttribute:
    """Verify that PriorityRule helpers tag lambdas with _source."""

    def test_provinces_left_source(self):
        cond = PriorityRule.provinces_left("<=", 4)
        assert hasattr(cond, "_source")
        assert cond._source == "PriorityRule.provinces_left('<=', 4)"

    def test_turn_number_source(self):
        cond = PriorityRule.turn_number(">=", 10)
        assert cond._source == "PriorityRule.turn_number('>=', 10)"

    def test_resources_source(self):
        cond = PriorityRule.resources("coins", ">=", 6)
        assert cond._source == "PriorityRule.resources('coins', '>=', 6)"

    def test_has_cards_source(self):
        cond = PriorityRule.has_cards(["Silver", "Gold"], 3)
        assert cond._source == "PriorityRule.has_cards(['Silver', 'Gold'], 3)"

    def test_always_true_source(self):
        cond = PriorityRule.always_true()
        assert cond._source == "PriorityRule.always_true()"

    def test_and_source(self):
        cond = PriorityRule.and_(
            PriorityRule.provinces_left("<=", 4),
            PriorityRule.resources("coins", ">=", 6),
        )
        assert "PriorityRule.and_(" in cond._source
        assert "PriorityRule.provinces_left" in cond._source
        assert "PriorityRule.resources" in cond._source


class TestSerialization:
    """Verify that save_strategy_as_python produces importable Python."""

    def test_round_trip(self, tmp_path):
        """Write a strategy, import it, and verify conditions still work."""
        from runner import save_strategy_as_python

        strategy = BaseStrategy()
        strategy.name = "TestRoundTrip"
        strategy.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver", PriorityRule.turn_number("<", 10)),
        ]
        strategy.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]
        strategy.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]

        out_file = tmp_path / "test_strategy.py"
        save_strategy_as_python(strategy, out_file, "TestStrategy")

        # Read the generated source and verify it contains no '<lambda>' or '<function'
        source = out_file.read_text()
        assert "<lambda" not in source, f"Source contains raw lambda repr:\n{source}"
        assert "<function" not in source, f"Source contains raw function repr:\n{source}"

        # The file should contain PriorityRule.resources etc.
        assert "PriorityRule.resources" in source
        assert "PriorityRule.provinces_left" in source

        # Import the generated module and verify it works
        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            mod = importlib.import_module("test_strategy")
            generated = mod.TestStrategy()
            assert generated.name == "TestRoundTrip"
            assert len(generated.gain_priority) == 4

            # Verify the conditions are callable and evaluate
            state = _make_mock_state()
            player = _make_mock_player(coins=8)
            province_rule = generated.gain_priority[0]
            assert province_rule.condition is not None
            assert callable(province_rule.condition)
            assert province_rule.condition(state, player) is True
        finally:
            sys.path.pop(0)
            sys.modules.pop("test_strategy", None)

    def test_none_conditions_serialize_cleanly(self, tmp_path):
        """Rules without conditions should not emit broken repr."""
        from runner import save_strategy_as_python

        strategy = BaseStrategy()
        strategy.name = "NoConditions"
        strategy.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        strategy.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        out_file = tmp_path / "no_cond_strategy.py"
        save_strategy_as_python(strategy, out_file, "NoCondStrategy")

        source = out_file.read_text()
        assert "<lambda" not in source
        assert "<function" not in source

        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            mod = importlib.import_module("no_cond_strategy")
            generated = mod.NoCondStrategy()
            assert len(generated.gain_priority) == 2
            assert generated.gain_priority[0].condition is None
        finally:
            sys.path.pop(0)
            sys.modules.pop("no_cond_strategy", None)


class TestMutationProducesCallableConditions:
    """Mutations should also produce callable conditions, not strings."""

    def test_mutated_conditions_are_callable(self):
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Laboratory"],
            population_size=1, generations=1, mutation_rate=1.0,  # Force mutations
        )
        strategy = trainer.create_random_strategy()

        # Mutate many times to exercise all paths
        for _ in range(20):
            strategy = trainer._mutate(strategy)

        for rule_list in [strategy.gain_priority, strategy.action_priority, strategy.trash_priority]:
            for rule in rule_list:
                assert rule.condition is None or callable(rule.condition), (
                    f"After mutation, condition for {rule.card_name} is {type(rule.condition)}"
                )
