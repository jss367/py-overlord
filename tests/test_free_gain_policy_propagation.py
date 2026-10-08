"""Nullable free-gain policy survives every generic strategy consumer."""

from copy import deepcopy
import random

import cloudpickle
import pytest

from dominion.ai.gain_context import FreeGainContext
from dominion.analysis.strategy_library import referenced_cards
from dominion.cards.registry import get_card
from dominion.runner import merge_baseline_panel
from dominion.simulation.adversarial_league import AdversarialLeague, genome_signature
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.parallel_games import _fired_indices
from dominion.simulation.strategic_genome import StrategicGenome, crossover_strategic_strategies, promote_legacy_strategy
from dominion.simulation.structured_genome import KingdomInfo, mutate_menu, normalize_menu
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.genome_simplification import simplify_strategy
from dominion.strategy.lint import cleanup_for_publication, lint_strategy
from dominion.strategy.rule_pruning import prune_unfired_rules, reset_fire_flags
from dominion.strategy.strategies.base_strategy import BaseStrategy
from scripts.league_evolve import _describe
from tests.test_shared_card_tactics import make_state


MODES = ["inherit", "fallback", "cap1", "cap2"]
INFO = KingdomInfo.from_kingdom(["Village", "Smithy", "Workshop"])


def configured(mode, *, typed=False):
    strategy = StrategicGenome().compile_into(BaseStrategy(), INFO) if typed else BaseStrategy()
    strategy.name = "same name"
    if not typed:
        strategy.gain_priority = [PriorityRule("Silver")]
        strategy.action_priority = [PriorityRule("Smithy")]
    strategy.free_gain_priority = None if mode == "inherit" else [] if mode == "fallback" else [
        PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 1 if mode == "cap1" else 2))
    ]
    return strategy


def free_identity(strategy):
    return genome_signature(strategy)[1]


def test_league_trainer_and_baseline_dedup_retain_all_nullable_policies():
    strategies = [configured(mode) for mode in MODES]
    assert len({genome_signature(s) for s in strategies}) == 4
    league = AdversarialLeague(capacity=4)
    for strategy in strategies:
        assert GeneticTrainer._genome_signature(strategy) == genome_signature(strategy)
        assert league.add(strategy, name=strategy.name, origin="seed")
        assert not league.add(deepcopy(strategy), name="duplicate", origin="champion")
    assert len(league.members) == 4
    panel = merge_baseline_panel(strategies[:1], strategies + [deepcopy(strategies[-1])])
    assert len(panel) == 4 and len({s.name for s in panel}) == 4
    assert len({free_identity(s) for s in panel}) == 4
    assert len(merge_baseline_panel(panel, strategies)) == 4
    assert all(s.name == "same name" for s in strategies)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("path", ["deepcopy", "worker", "simplify", "publication"])
def test_clone_and_cleanup_preserve_nullable_identity_and_decisions(mode, path):
    strategy = configured(mode)
    clone = {"deepcopy": deepcopy, "worker": lambda s: cloudpickle.loads(cloudpickle.dumps(s)),
             "simplify": simplify_strategy, "publication": cleanup_for_publication}[path](strategy)
    assert free_identity(clone) == free_identity(strategy)
    if clone.free_gain_priority is not None:
        assert clone.free_gain_priority is not strategy.free_gain_priority
    state, player = make_state(clone, ("Village", "Smithy", "Silver"))
    player.discard = [get_card("Smithy")]
    context = FreeGainContext.build(state, player, "Workshop")
    choices = [get_card(n) for n in state.supply]
    assert clone.choose_free_gain(state, player, choices, context).name == (
        "Silver" if mode == "inherit" else "Smithy" if mode == "cap2" else "Village")
    if mode.startswith("cap"):
        assert "Smithy" in referenced_cards(clone)
    description = _describe(clone)["free_gain_priority"]
    assert (description is None) == (mode == "inherit")
    assert (description == []) == (mode == "fallback")


@pytest.mark.parametrize("first", MODES)
@pytest.mark.parametrize("second", MODES)
@pytest.mark.parametrize("path", ["legacy", "typed", "typed-direct"])
def test_crossover_inherits_complete_nullable_setting_without_aliasing(first, second, path, monkeypatch):
    a, b = configured(first, typed=path != "legacy"), configured(second, typed=path != "legacy")
    monkeypatch.setattr(random, "random", lambda: 0.0)
    if path == "typed-direct":
        child = crossover_strategic_strategies(a, b, INFO)
    else:
        trainer = GeneticTrainer.__new__(GeneticTrainer)
        trainer.structured_genome = path == "typed"
        trainer._kingdom_info = INFO
        child = trainer._crossover(a, b)
    assert free_identity(child) == free_identity(b)
    if child.free_gain_priority is not None:
        assert child.free_gain_priority is not a.free_gain_priority
        assert child.free_gain_priority is not b.free_gain_priority


def test_inherited_free_gain_crossover_adds_no_random_draw(monkeypatch):
    draws = []
    monkeypatch.setattr(random, "random", lambda: (draws.append(1), 0.0)[1])
    trainer = GeneticTrainer.__new__(GeneticTrainer)
    trainer.structured_genome = False
    a, b = configured("inherit"), configured("inherit")
    trainer._crossover(a, b)
    inherited_draws = len(draws)
    draws.clear()
    b.free_gain_priority = []
    trainer._crossover(a, b)
    assert len(draws) == inherited_draws + 1


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("typed", [False, True])
def test_mutation_normalization_and_promotion_preserve_side_policy(mode, typed):
    strategy = configured(mode, typed=typed)
    identity = free_identity(strategy)
    promote_legacy_strategy(strategy, INFO)
    mutate_menu(strategy, INFO, 1.0, rng=random.Random(17))
    normalize_menu(strategy, INFO)
    assert free_identity(strategy) == identity
    trainer = GeneticTrainer.__new__(GeneticTrainer)
    trainer.structured_genome = False
    trainer.kingdom_cards = ["Village", "Smithy", "Workshop"]
    trainer.mutation_rate = 0.0
    trainer._kingdom_ways = []
    trainer._mutate(strategy)
    trainer._normalize(strategy)
    assert free_identity(strategy) == identity


def test_free_gain_rule_fires_cross_worker_boundary_and_prunes_with_existing_floor():
    strategy = configured("cap2")
    strategy.free_gain_priority.append(PriorityRule("Village"))
    reset_fire_flags(strategy)
    state, player = make_state(strategy, ("Smithy", "Silver"))
    strategy.choose_free_gain(state, player, [get_card("Smithy"), get_card("Silver")],
                              FreeGainContext.build(state, player, "Workshop"))
    assert _fired_indices(cloudpickle.loads(cloudpickle.dumps(strategy)))["free_gain_priority"] == [0]
    prune_unfired_rules(strategy, min_rules=1)
    assert [r.card_name for r in strategy.free_gain_priority] == ["Smithy"]
    reset_fire_flags(strategy)
    assert "free_gain_priority" not in _fired_indices(strategy)
    for mode in ["inherit", "fallback"]:
        other = configured(mode)
        prune_unfired_rules(other)
        assert free_identity(other) == free_identity(configured(mode))


def test_free_gain_lint_and_syntactic_simplification_share_policy_rules():
    strategy = configured("fallback")
    strategy.free_gain_priority = [PriorityRule("Smithy"), PriorityRule("Smithy")]
    assert any(w.list_name == "free_gain" for w in lint_strategy(strategy))
    assert len(simplify_strategy(strategy).free_gain_priority) == 1
