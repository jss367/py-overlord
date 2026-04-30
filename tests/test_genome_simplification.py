"""Tests for genome simplification.

These verify behavior-preserving cleanups of priority lists produced by the
genetic trainer: deduplication of identical rules and elimination of rules
unreachable behind an earlier unconditional rule for the same card.
"""

from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.genome_simplification import simplify_strategy
from dominion.strategy.strategies.base_strategy import BaseStrategy


def _make_strategy(gain=None, action=None, treasure=None, trash=None) -> BaseStrategy:
    s = BaseStrategy()
    s.name = "Test"
    s.gain_priority = list(gain or [])
    s.action_priority = list(action or [])
    s.treasure_priority = list(treasure or [])
    s.trash_priority = list(trash or [])
    return s


def _rule_signatures(rules):
    return [(r.card, getattr(r.condition, "_source", None)) for r in rules]


class TestDedupe:
    def test_drops_later_rule_with_identical_card_and_condition(self):
        cond = PriorityRule.resources("coins", ">=", 8)
        # Two identical Province rules — second one is unreachable.
        rules = [
            PriorityRule("Province", cond),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Silver"),
        ]
        s = simplify_strategy(_make_strategy(gain=rules))
        assert _rule_signatures(s.gain_priority) == [
            ("Province", "PriorityRule.resources('coins', '>=', 8)"),
            ("Silver", None),
        ]

    def test_keeps_same_card_with_distinct_conditions(self):
        rules = [
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 2)),
        ]
        s = simplify_strategy(_make_strategy(gain=rules))
        assert len(s.gain_priority) == 2

    def test_dedupes_unconditional_repeats(self):
        rules = [
            PriorityRule("Silver"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
            PriorityRule("Silver"),
        ]
        s = simplify_strategy(_make_strategy(gain=rules))
        assert _rule_signatures(s.gain_priority) == [
            ("Silver", None),
            ("Copper", None),
        ]


class TestUnconditionalDominance:
    def test_drops_later_rules_for_same_card_after_unconditional(self):
        rules = [
            PriorityRule("Province"),  # always fires when Province is in choices
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Province", PriorityRule.provinces_left("<=", 4)),
        ]
        s = simplify_strategy(_make_strategy(gain=rules))
        assert _rule_signatures(s.gain_priority) == [("Province", None)]

    def test_does_not_drop_later_rules_for_other_cards(self):
        # Unconditional Silver only dominates later Silver rules. The
        # conditional Gold rule is unaffected.
        rules = [
            PriorityRule("Silver"),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule("Silver", PriorityRule.provinces_left("<=", 2)),  # dropped (Silver dominated)
            PriorityRule("Copper"),  # different card; kept
        ]
        s = simplify_strategy(_make_strategy(gain=rules))
        cards = [r.card for r in s.gain_priority]
        assert cards == ["Silver", "Gold", "Copper"]


class TestPreservesUnrelatedLists:
    def test_simplifies_each_priority_list_independently(self):
        gain_rules = [
            PriorityRule("Province"),
            PriorityRule("Province"),  # dropped
        ]
        action_rules = [
            PriorityRule("Village"),
            PriorityRule("Village"),  # dropped
        ]
        treasure_rules = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
        ]
        trash_rules = [
            PriorityRule("Curse"),
            PriorityRule("Curse"),  # dropped
        ]
        s = simplify_strategy(
            _make_strategy(
                gain=gain_rules,
                action=action_rules,
                treasure=treasure_rules,
                trash=trash_rules,
            )
        )
        assert [r.card for r in s.gain_priority] == ["Province"]
        assert [r.card for r in s.action_priority] == ["Village"]
        assert [r.card for r in s.treasure_priority] == ["Gold", "Silver"]
        assert [r.card for r in s.trash_priority] == ["Curse"]


class TestEvolvedExample:
    """Reproduce the exact pattern observed in a real evolved strategy."""

    def test_three_province_rules_collapse_to_one(self):
        rules = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Cauldron", PriorityRule.turn_number("<=", 11)),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),  # dup
            PriorityRule("Province"),  # unconditional
            PriorityRule("Duchy", PriorityRule.has_cards(["Duchy", "Province", "Silver"], 2)),
        ]
        s = simplify_strategy(_make_strategy(gain=rules))
        sigs = _rule_signatures(s.gain_priority)
        # After simplification: dup is gone; conditional Province + unconditional Province
        # both kept (the conditional fires first when satisfied, otherwise falls through to D).
        assert sigs == [
            ("Province", "PriorityRule.resources('coins', '>=', 8)"),
            ("Cauldron", "PriorityRule.turn_number('<=', 11)"),
            ("Province", None),
            ("Duchy", "PriorityRule.has_cards(['Duchy', 'Province', 'Silver'], 2)"),
        ]


class TestDoesNotMutateInput:
    def test_returns_a_new_strategy_without_mutating_original(self):
        original_rules = [
            PriorityRule("Province"),
            PriorityRule("Province"),
        ]
        original = _make_strategy(gain=original_rules)
        simplified = simplify_strategy(original)
        # Original is untouched.
        assert len(original.gain_priority) == 2
        # Simplified is reduced.
        assert len(simplified.gain_priority) == 1


class TestTrainerIntegration:
    """Verify the GeneticTrainer applies simplification each generation."""

    def test_population_is_simplified_before_evaluation(self, monkeypatch):
        from dominion.simulation.genetic_trainer import GeneticTrainer

        trainer = GeneticTrainer(
            ["Village"], population_size=2, generations=1, games_per_eval=1
        )

        # Plant a strategy with redundant rules in the initial population by
        # capturing its evaluated form.
        trainer.create_random_strategy = lambda: _make_strategy(
            gain=[PriorityRule("Province"), PriorityRule("Province")],
            treasure=[PriorityRule("Gold")],
        )
        seen_lengths: list[int] = []

        def fake_evaluate(strategy):
            seen_lengths.append(len(strategy.gain_priority))
            return 50.0

        monkeypatch.setattr(trainer, "evaluate_strategy", fake_evaluate)
        monkeypatch.setattr(
            trainer, "create_next_generation", lambda *a, **k: a[0]
        )
        monkeypatch.setattr(
            trainer, "_apply_fitness_sharing", lambda *a, **k: a[1]
        )

        trainer.train()

        # Every evaluated strategy had its duplicate Province rule removed.
        assert seen_lengths
        assert all(length == 1 for length in seen_lengths)

    def test_simplification_disabled_via_flag(self, monkeypatch):
        from dominion.simulation.genetic_trainer import GeneticTrainer

        trainer = GeneticTrainer(
            ["Village"],
            population_size=2,
            generations=1,
            games_per_eval=1,
            simplify_genomes=False,
        )
        trainer.create_random_strategy = lambda: _make_strategy(
            gain=[PriorityRule("Province"), PriorityRule("Province")],
            treasure=[PriorityRule("Gold")],
        )
        seen_lengths: list[int] = []

        def fake_evaluate(strategy):
            seen_lengths.append(len(strategy.gain_priority))
            return 50.0

        monkeypatch.setattr(trainer, "evaluate_strategy", fake_evaluate)
        monkeypatch.setattr(
            trainer, "create_next_generation", lambda *a, **k: a[0]
        )
        monkeypatch.setattr(
            trainer, "_apply_fitness_sharing", lambda *a, **k: a[1]
        )

        trainer.train()

        # When disabled, the duplicate Province rule remains in the genome.
        assert seen_lengths
        assert all(length == 2 for length in seen_lengths)
