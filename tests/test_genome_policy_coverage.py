"""Boundaries and persistence for the Oslo reference decisions in schema 2."""

from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
import random

import cloudpickle

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.analysis.strategic_genome_audit import audit_equivalence, oslo_reference_genome
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.runner import save_strategy_as_python
from dominion.simulation.adversarial_league import genome_signature
from dominion.simulation.reflective_strategy_search import board_seed, compile_genome, genome_text, parse_genome
from dominion.simulation.strategic_genome import (
    StrategicGenome, crossover_strategic_strategies, mutate_strategic_strategy,
    promote_legacy_strategy, random_strategic_genome, synchronize_strategic_genome,
)
from dominion.simulation.structured_genome import KingdomInfo
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy
from generated_strategies.oslo_workers_village_magnate_engine import (
    OsloWorkersVillageMagnateMultiColonyEngine, OsloWorkersVillageMagnateRefinedEngine,
)


@pytest.fixture
def info():
    return KingdomInfo.from_kingdom(load_board("boards/oslo.txt").kingdom_cards)


def setup(genome, info):
    strategy = compile_genome(genome_text(genome), info)
    ai = GeneticAI(strategy)
    state = GameState(players=[])
    state.initialize_game([ai], [get_card(card) for card in info.kingdom_cards])
    player = state.players[0]
    player.hand, player.deck, player.discard, player.in_play = [], [], [], []
    state.turn_number = 5
    return strategy, ai, state, player


def condition(strategy, card):
    return next(r.condition for r in strategy.gain_priority if r.card_name == card)


def test_resource_gate_uses_live_prices_buys_commitment_and_fallback(info):
    strategy, _, state, player = setup(oslo_reference_genome(multi_colony=True), info)
    gate = condition(strategy, "Colony")
    for setup_discount, turn_discount in ((0, 0), (2, 0), (2, 3), (20, 0)):
        state.setup_card_cost_reduction = setup_discount
        player.cost_reduction = turn_discount
        cost = state.get_card_cost(player, get_card("Colony"))
        player.buys, player.coins = 4, 4 * cost
        assert gate(state, player)
        player.buys = 3
        assert not gate(state, player)
        player.buys, player.coins = 4, 4 * cost - 1
        assert not gate(state, player)
    player.buys, player.coins = 1, 0
    player.discard = [get_card("Colony")]
    assert gate(state, player)
    player.discard = []
    state.turn_number = 19
    assert not gate(state, player)
    state.turn_number = 20
    assert gate(state, player)
    restored = eval(gate._source, {"PriorityRule": PriorityRule})
    assert restored(state, player)


def test_opening_gain_limit_and_counted_dependency(info):
    strategy, _, state, player = setup(oslo_reference_genome(), info)
    opening = condition(strategy, "Anvil")
    assert opening(state, player)
    player.cards_gained_this_turn = 1
    assert not opening(state, player)
    player.cards_gained_this_turn = 0
    state.turn_number = 8
    assert not opening(state, player)
    court = condition(strategy, "King's Court")
    for count in (0, 2, 3):
        player.deck = [get_card("Magnate") for _ in range(count)]
        assert court(state, player) == (count >= 3)


def test_balanced_anvil_ratios_caps_ties_fallback_and_discard(info):
    genome = oslo_reference_genome()
    genome.tactics.balanced_gain_targets[1].copies = 4
    strategy, ai, state, player = setup(genome, info)
    village, magnate, silver, copper = map(get_card, ("Workers' Village", "Magnate", "Silver", "Copper"))
    player.deck = [get_card("Workers' Village") for _ in range(3)] + [get_card("Magnate") for _ in range(2)]
    # 3/7 < 2/4, even though Magnate has fewer absolute copies.
    assert ai.choose_anvil_gain(state, player, [magnate, village]) is village
    player.deck = []
    assert ai.choose_anvil_gain(state, player, [magnate, village]) is magnate
    player.deck = [get_card("Workers' Village") for _ in range(7)] + [get_card("Magnate") for _ in range(7)]
    assert ai.choose_anvil_gain(state, player, [silver, village, magnate]) is silver
    player.deck = []
    assert ai.choose_anvil_option(state, player, [copper], [magnate, village]) == (copper, magnate)
    reserve = next(r.condition for r in strategy.treasure_priority if r.card_name == "Copper")
    assert reserve(state, player)
    player.in_play = [get_card("Anvil")]
    assert not reserve(state, player)
    state.supply["Workers' Village"] = state.supply["Magnate"] = 0
    assert reserve(state, player)


@pytest.mark.parametrize("hand,expected", [
    (["King's Court", "Grand Market"], "King's Court"),
    (["King's Court", "King's Court", "Grand Market"], "King's Court"),
    (["King's Court", "Workers' Village", "Magnate"], "Workers' Village"),
])
def test_multiplier_protection_only_affects_main_phase(info, hand, expected):
    strategy, _, state, player = setup(oslo_reference_genome(multi_colony=True), info)
    choices = [get_card(card) for card in hand]
    state._choosing_main_action_phase = True
    assert strategy.choose_action(state, player, choices).name == expected
    state._choosing_main_action_phase = False
    if "Grand Market" in hand:
        assert strategy.choose_action(state, player, choices).name == "Grand Market"


def test_purchase_balance_boundaries(info):
    genome = oslo_reference_genome()
    target = next(t for t in genome.build_targets if t.card == "Workers' Village")
    target.balance_card, target.balance_max_lead = "Magnate", -1
    strategy, _, state, player = setup(genome, info)
    gate = condition(strategy, "Workers' Village")
    assert not gate(state, player)
    player.deck = [get_card("Magnate")]
    assert gate(state, player)
    player.hand = [get_card("Workers' Village")]
    assert not gate(state, player)


@pytest.mark.parametrize("clean", [False, True])
def test_export_reload_and_fingerprints_preserve_tactical_policies(info, tmp_path, clean):
    strategy = oslo_reference_genome(multi_colony=True).compile_into(BaseStrategy(), info)
    path = tmp_path / "exported.py"
    save_strategy_as_python(strategy, path, clean_for_publication=clean)
    spec = importlib.util.spec_from_file_location("audit_export", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reloaded = module.GeneratedStrategy()
    assert genome_signature(reloaded) == genome_signature(strategy)
    assert not promote_legacy_strategy(reloaded, info)  # never silently drop data policies
    for attribute in ("balanced_gain_targets", "protected_multipliers"):
        changed = deepcopy(strategy)
        setattr(changed, attribute, [])
        assert genome_signature(changed) != genome_signature(strategy)
    assert synchronize_strategic_genome(strategy, info)
    rebuilt = strategy._strategic_genome.compile_into(BaseStrategy(), info)
    assert genome_signature(rebuilt) == genome_signature(strategy)
    StrategicGenome().compile_into(strategy, info)
    assert strategy.balanced_gain_source is None
    assert strategy.protected_multipliers == []


def test_new_policies_are_reachable_and_round_trip_in_genetic_operators(info):
    rng, seen = random.Random(719), set()
    strategy = oslo_reference_genome(multi_colony=True).compile_into(BaseStrategy(), info)
    for _ in range(120):
        mutant = deepcopy(strategy)
        mutate_strategic_strategy(mutant, info, 0.8, rng)
        genome = mutant._strategic_genome
        assert asdict(parse_genome(genome_text(genome), info)) == asdict(genome)
        seen.add(genome.greening.colony_mode)
        if any(t.balance_card for t in genome.build_targets):
            seen.add("balance")
        if genome.tactics.balanced_gain_source:
            seen.add("gains")
        child = crossover_strategic_strategies(strategy, mutant, info, rng)
        assert genome_signature(child) == genome_signature(
            child._strategic_genome.compile_into(BaseStrategy(), info))
    assert {"always", "multi_buy", "balance", "gains"} <= seen


def test_legacy_schema_and_search_mode_remain_available(info):
    old = board_seed(load_board("boards/oslo.txt"))
    text = genome_text(old, 1)
    assert json.loads(text)["schema_version"] == 1
    assert asdict(parse_genome(text, info)) == asdict(old)
    del old.tactics
    del old.treasure_reserve
    reloaded = cloudpickle.loads(cloudpickle.dumps(old))
    assert reloaded.compile_into(BaseStrategy(), info).balanced_gain_source is None
    for field in ("treasure_reserve", "tactics"):
        payload = json.loads(text)
        payload["genome"][field] = None
        with pytest.raises(ValueError):
            parse_genome(json.dumps(payload), info)
    with pytest.raises(ValueError):
        genome_text(oslo_reference_genome(), 1)
    info.strategy_schema_version = 1
    for seed in range(20):
        genome = random_strategic_genome(info, random.Random(seed))
        assert parse_genome(genome_text(genome, 1), info)


@pytest.mark.parametrize("field,value", [
    ("balanced_gain_source", "Expand"),
    ("balanced_gain_targets", []),
    ("protected_multipliers", ["Magnate"]),
    ("protected_multipliers", ["King's Court", "King's Court"]),
])
def test_invalid_tactical_fields_are_rejected(info, field, value):
    payload = json.loads(genome_text(oslo_reference_genome()))
    payload["genome"]["tactics"][field] = value
    with pytest.raises(ValueError):
        parse_genome(json.dumps(payload), info)


def test_non_gainer_treasure_reserve_is_rejected(info):
    payload = json.loads(genome_text(oslo_reference_genome()))
    payload["genome"]["treasure_reserve"]["gainer"] = "Workers' Village"
    with pytest.raises(ValueError, match="gainer"):
        parse_genome(json.dumps(payload), info)


@pytest.mark.parametrize("multi,reference", [
    (False, OsloWorkersVillageMagnateRefinedEngine),
    (True, OsloWorkersVillageMagnateMultiColonyEngine),
])
def test_reference_decision_sequences_match_generic_compilation(info, tmp_path, multi, reference):
    strategy = compile_genome(genome_text(oslo_reference_genome(multi_colony=multi)), info)
    assert type(strategy) is BaseStrategy
    assert not hasattr(strategy, "choose_anvil_gain")
    before = random.getstate()
    result = audit_equivalence(load_board("boards/oslo.txt"), reference(), strategy,
                               {"Reference": reference()}, pairs=1, log_dir=tmp_path)
    assert random.getstate() == before
    assert result["equivalent"], result["games"]
    assert result["decisions_compared"] > 100
