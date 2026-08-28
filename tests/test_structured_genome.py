"""Tests for the structured "buy menu" genome operators.

The structured genome constrains the GA's search space: random individuals
are coherent menus (greening block + capped kingdom picks over a treasure
backbone), mutations are menu edits from a curated gate vocabulary, and
normalization enforces the invariants every viable strategy needs.
"""

from __future__ import annotations

import random
import types

from dominion.cards.registry import get_card
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.structured_genome import (
    KingdomInfo,
    kingdom_similarity,
    mutate_menu,
    normalize_menu,
    random_menu_strategy,
)
from dominion.simulation.strategic_genome import (
    BuildTarget,
    EconomyPlan,
    EndgamePlan,
    GreeningPlan,
    OpeningTarget,
    StrategicGenome,
    crossover_strategic_strategies,
    mutate_strategic_strategy,
    promote_legacy_strategy,
    synchronize_strategic_genome,
)
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy

KINGDOM = ["Village", "Smithy", "Market", "Festival", "Laboratory", "Witch", "Chapel", "Moat"]
COLONY_KINGDOM = KINGDOM + ["Colony", "Platinum"]


def _info() -> KingdomInfo:
    return KingdomInfo.from_kingdom(KINGDOM)


def _colony_info() -> KingdomInfo:
    return KingdomInfo.from_kingdom(COLONY_KINGDOM)


def _mock_state(turn_number=5, provinces_left=8):
    state = types.SimpleNamespace()
    state.turn_number = turn_number
    state.supply = {"Province": provinces_left}
    state.empty_piles = 0
    state.players = []
    return state


def _mock_player():
    player = types.SimpleNamespace()
    player.coins = 3
    player.actions = 1
    player.buys = 1
    player.hand = []
    player.in_play = []
    player.count_in_deck = lambda _c: 0
    player.all_cards = lambda: []
    player.get_victory_points = lambda _g=None: 3
    player.actions_gained_this_turn = 0
    player.cards_gained_this_turn = 0
    return player


class _DeterministicRng:
    """Small RNG stub for asserting exact semantic operator outcomes."""

    def random(self):
        return 0.0

    def choice(self, values):
        return values[-1]

    def randint(self, _low, high):
        return high

    def randrange(self, _stop):
        return 0


class TestKingdomInfo:
    def test_role_classification(self):
        info = _info()
        assert "Village" in info.villages          # +2 actions
        assert "Festival" in info.villages         # +2 actions
        assert "Market" in info.cantrips           # +1 action
        assert "Laboratory" in info.cantrips       # +1 action
        assert "Smithy" in info.terminal_draw      # 0 actions, +3 cards
        assert "Witch" in info.terminal_draw       # 0 actions, +2 cards
        assert "Chapel" in info.other_terminals
        assert set(info.gainable) == set(KINGDOM)

    def test_basic_cards_are_not_picks(self):
        info = KingdomInfo.from_kingdom(["Village", "Copper", "Province"])
        assert info.gainable == ["Village"]

    def test_unknown_cards_are_skipped(self):
        info = KingdomInfo.from_kingdom(["Village", "NotACard"])
        assert info.gainable == ["Village"]

    def test_colony_and_platinum_are_basic_not_picks(self):
        info = KingdomInfo.from_kingdom(["Village", "Colony", "Platinum"])
        assert info.gainable == ["Village"]
        assert info.has_colony is True
        assert info.has_platinum is True

    def test_colony_flags_default_off(self):
        info = _info()
        assert info.has_colony is False
        assert info.has_platinum is False


class TestRandomMenuStrategy:
    def test_menus_are_coherent(self):
        random.seed(3)
        info = _info()
        for _ in range(30):
            s = random_menu_strategy(info)
            names = [r.card_name for r in s.gain_priority]
            # Province exists near the front; explicit opening/endgame rules
            # are allowed to precede it in the phase-aware genome.
            assert "Province" in names
            assert names.index("Province") <= 3
            # Silver remains the fallback economy. Gold may be deliberately
            # omitted for rushes such as Rebuild/Duchy.
            assert "Silver" in names
            # No junk buys.
            assert "Copper" not in names and "Curse" not in names
            # Picks are kingdom cards.
            assert all(n in set(KINGDOM) | {"Province", "Duchy", "Estate", "Gold", "Silver"} for n in names)

    def test_kingdom_picks_are_capped(self):
        random.seed(4)
        info = _info()
        s = random_menu_strategy(info)
        for rule in s.gain_priority:
            if rule.card_name in KINGDOM:
                source = getattr(rule.condition, "_source", "")
                assert "max_in_deck" in source, (
                    f"{rule.card_name} has no deck cap: {source!r}"
                )

    def test_action_priority_orders_villages_first(self):
        random.seed(5)
        info = _info()
        s = random_menu_strategy(info)
        names = [r.card_name for r in s.action_priority]
        assert set(names) == set(info.action_cards)
        village_idx = [names.index(c) for c in info.villages]
        terminal_idx = [names.index(c) for c in info.terminal_draw + info.other_terminals]
        assert max(village_idx) < min(terminal_idx)

    def test_conditions_are_callable_and_evaluate(self):
        random.seed(6)
        info = _info()
        state, player = _mock_state(), _mock_player()
        for _ in range(20):
            s = random_menu_strategy(info)
            for rule_list in (s.gain_priority, s.action_priority, s.trash_priority):
                for rule in rule_list:
                    if rule.condition is not None:
                        assert callable(rule.condition)
                        assert isinstance(rule.condition(state, player), bool)
                        assert hasattr(rule.condition, "_source")

    def test_treasure_priority_plays_gold_before_copper(self):
        random.seed(7)
        s = random_menu_strategy(_info())
        names = [r.card_name for r in s.treasure_priority]
        assert names.index("Gold") < names.index("Silver") < names.index("Copper")

    def test_colony_board_menus(self):
        random.seed(15)
        info = _colony_info()
        for _ in range(30):
            s = random_menu_strategy(info)
            names = [r.card_name for r in s.gain_priority]
            # Colony leads the normal greening block. Explicit opening/endgame
            # rules may precede it, but Colony itself remains unconditional.
            colony_rule = next(rule for rule in s.gain_priority if rule.card_name == "Colony")
            assert colony_rule.condition is None
            assert "Province" in names
            # Platinum joins the backbone and is never a capped pick. Gold may
            # be deliberately omitted by a typed rush plan.
            if "Gold" in names:
                assert names.index("Platinum") < names.index("Gold")
            for rule in s.gain_priority:
                if rule.card_name in ("Colony", "Platinum"):
                    source = getattr(rule.condition, "_source", "") if rule.condition else ""
                    assert "max_in_deck" not in source
            # Platinum is played before Gold.
            treasures = [r.card_name for r in s.treasure_priority]
            assert treasures.index("Platinum") < treasures.index("Gold")


class TestStrategicGenomeRepresentability:
    def test_exact_early_single_card_opening_is_one_semantic_block(self):
        genome = StrategicGenome(
            openings=[OpeningTarget("Chapel", copies=1, through_turn=2)],
            greening=GreeningPlan(duchy_mode="never"),
            action_order=["Chapel"],
            treasure_order=["Gold", "Silver", "Copper"],
        )
        strategy = genome.compile_into(BaseStrategy(), _info())

        chapel = strategy.gain_priority[0]
        assert chapel.card_name == "Chapel"
        source = chapel.condition._source
        assert "max_in_deck('Chapel', 1)" in source
        assert "turn_number('<=', 2)" in source

    def test_rebuild_rush_is_representable_without_custom_hooks(self):
        info = KingdomInfo.from_kingdom(["Rebuild", "Cellar", "Moat"])
        genome = StrategicGenome(
            build_targets=[
                BuildTarget(
                    "Rebuild", copies=2, priority_band="before_duchy"
                )
            ],
            economy=EconomyPlan(buy_gold=False, buy_silver=True),
            greening=GreeningPlan(
                province_mode="always",
                duchy_mode="always",
                estate_mode="threshold",
                estate_threshold=2,
            ),
            action_order=["Rebuild"],
            treasure_order=["Gold", "Silver", "Copper"],
        )
        strategy = genome.compile_into(BaseStrategy(), info)

        assert [rule.card_name for rule in strategy.gain_priority] == [
            "Province", "Rebuild", "Duchy", "Estate", "Silver"
        ]
        assert "max_in_deck('Rebuild', 2)" in strategy.gain_priority[1].condition._source

    def test_delayed_build_target_is_representable(self):
        genome = StrategicGenome(
            build_targets=[
                BuildTarget(
                    "Taskmaster",
                    copies=4,
                    from_turn=5,
                    while_provinces_above=4,
                    priority_band="before_silver",
                )
            ],
            treasure_order=["Gold", "Silver", "Copper"],
        )
        strategy = genome.compile_into(
            BaseStrategy(), KingdomInfo.from_kingdom(["Taskmaster"])
        )

        names = [rule.card_name for rule in strategy.gain_priority]
        assert names.index("Gold") < names.index("Taskmaster") < names.index("Silver")
        taskmaster = next(
            rule for rule in strategy.gain_priority if rule.card_name == "Taskmaster"
        )
        assert "turn_number('>=', 5)" in taskmaster.condition._source
        assert "provinces_left('>', 4)" in taskmaster.condition._source

    def test_build_window_normalizes_independently_mutated_bounds(self):
        target = BuildTarget("Smithy", copies=2, from_turn=12, through_turn=6)
        genome = StrategicGenome(
            build_targets=[target],
            treasure_order=["Gold", "Silver", "Copper"],
        )

        strategy = genome.compile_into(BaseStrategy(), _info())
        source = next(
            rule.condition._source
            for rule in strategy.gain_priority
            if rule.card_name == "Smithy"
        )

        assert "turn_number('>=', 6)" in source
        assert "turn_number('<=', 12)" in source

    def test_pile_pressure_and_tactical_close_are_independent(self):
        genome = StrategicGenome(
            greening=GreeningPlan(
                duchy_mode="never",
                estate_mode="pile_pressure",
                estate_empty_piles=2,
            ),
            endgame=EndgamePlan(estate_pileout=True),
            treasure_order=["Gold", "Silver", "Copper"],
        )
        strategy = genome.compile_into(BaseStrategy(), _info())
        estate_rules = [
            rule for rule in strategy.gain_priority if rule.card_name == "Estate"
        ]

        assert len(estate_rules) == 2
        assert "pile_count" in estate_rules[0].condition._source
        assert estate_rules[1].condition._source == (
            "PriorityRule.empty_piles('>=', 2)"
        )

    def test_representable_legacy_strategy_is_promoted_without_rule_changes(self):
        from dominion.strategy.strategies.calibration_known_best import RebuildRush

        strategy = RebuildRush()
        before = GeneticTrainer._genome_signature(strategy)
        info = KingdomInfo.from_kingdom(["Rebuild", "Cellar", "Moat"])

        assert promote_legacy_strategy(strategy, info) is True
        assert GeneticTrainer._genome_signature(strategy) == before
        assert strategy._strategic_genome.build_targets == [
            BuildTarget("Rebuild", 2, priority_band="before_duchy")
        ]

    def test_custom_conditional_action_strategy_is_not_promoted(self):
        from dominion.strategy.strategies.calibration_known_best import (
            ChapelWitchClassic,
        )

        strategy = ChapelWitchClassic()
        info = KingdomInfo.from_kingdom(["Chapel", "Witch", "Cellar"])

        assert promote_legacy_strategy(strategy, info) is False
        assert not hasattr(strategy, "_strategic_genome")

    def test_pileout_policy_can_override_normal_province_buy(self):
        genome = StrategicGenome(
            greening=GreeningPlan(duchy_mode="never"),
            endgame=EndgamePlan(
                estate_pileout=True,
                pileout_max_remaining=1,
                pileout_min_score_diff=0,
            ),
            treasure_order=["Gold", "Silver", "Copper"],
        )
        strategy = genome.compile_into(BaseStrategy(), _info())
        estate = strategy.gain_priority[0]
        assert estate.card_name == "Estate"

        state = _mock_state()
        state.empty_piles = 2
        player = _mock_player()
        state.players = [player]

        assert estate.condition(state, player) is False
        state.supply["Estate"] = 1
        assert estate.condition(state, player) is True

        state.supply["Estate"] = 2
        assert estate.condition(state, player) is False

    def test_semantic_mutation_recompiles_from_typed_genome(self):
        strategy = StrategicGenome(
            build_targets=[BuildTarget("Smithy", 2)],
            economy=EconomyPlan(buy_gold=True),
            action_order=["Smithy"],
            treasure_order=["Gold", "Silver", "Copper"],
        ).compile_into(BaseStrategy(), _info())

        assert mutate_strategic_strategy(
            strategy, _info(), rate=1.0, rng=_DeterministicRng()
        ) is True
        assert strategy._strategic_genome.economy.buy_gold is False
        target = strategy._strategic_genome.build_targets[0]
        assert target.copies == 3
        assert target.from_turn == 11
        assert target.through_turn == 16
        assert target.while_provinces_above == 6
        assert target.requires_card is not None
        assert target.priority_band == "fallback"
        assert strategy._strategic_genome.economy.buy_silver is False
        assert strategy._strategic_genome.economy.silver_through_turn == 16
        assert strategy._strategic_genome.economy.gold_cap == 6
        assert strategy._strategic_genome.trash.trash_curse is False
        assert strategy._strategic_genome.trash.copper_after_treasures == 5
        assert strategy._strategic_genome.treasure_order != [
            "Gold", "Silver", "Copper"
        ]
        assert all(rule.card_name != "Gold" for rule in strategy.gain_priority)
        smithy = next(
            rule for rule in strategy.gain_priority if rule.card_name == "Smithy"
        )
        assert "max_in_deck('Smithy', 3)" in smithy.condition._source

    def test_crossover_swaps_whole_modules(self):
        first = StrategicGenome(
            build_targets=[BuildTarget("Smithy", 2)],
            action_order=["Smithy"],
            treasure_order=["Gold", "Silver", "Copper"],
        ).compile_into(BaseStrategy(), _info())
        second = StrategicGenome(
            build_targets=[BuildTarget("Witch", 1)],
            action_order=["Witch"],
            treasure_order=["Gold", "Silver", "Copper"],
        ).compile_into(BaseStrategy(), _info())
        child = crossover_strategic_strategies(
            first, second, _info(), rng=_DeterministicRng()
        )

        assert child is not None
        assert [
            target.card for target in child._strategic_genome.build_targets
        ] == ["Witch"]
        assert child._strategic_genome.action_order == ["Witch"]
        assert any(rule.card_name == "Witch" for rule in child.gain_priority)
        assert all(rule.card_name != "Smithy" for rule in child.gain_priority)

    def test_pruned_target_is_not_resurrected_by_semantic_crossover(self):
        from dominion.strategy.rule_pruning import prune_unfired_rules

        genome = StrategicGenome(
            build_targets=[BuildTarget("Smithy", 2)],
            greening=GreeningPlan(duchy_mode="never"),
            action_order=["Smithy"],
            treasure_order=["Gold", "Silver", "Copper"],
        )
        parent = genome.compile_into(BaseStrategy(), _info())
        for rules in (
            parent.gain_priority,
            parent.action_priority,
            parent.treasure_priority,
            parent.trash_priority,
        ):
            for rule in rules:
                rule._fired = rule.card_name != "Smithy"

        prune_unfired_rules(parent, min_rules=0)
        synchronize_strategic_genome(parent, _info())
        child = crossover_strategic_strategies(parent, parent, _info())

        assert child is not None
        assert all(
            target.card != "Smithy"
            for target in child._strategic_genome.build_targets
        )
        assert all(rule.card_name != "Smithy" for rule in child.gain_priority)

    def test_pruned_platinum_is_not_resurrected_by_semantic_crossover(self):
        from dominion.strategy.rule_pruning import prune_unfired_rules

        parent = StrategicGenome(
            greening=GreeningPlan(duchy_mode="never"),
            economy=EconomyPlan(prefer_platinum=True),
            treasure_order=["Platinum", "Gold", "Silver", "Copper"],
        ).compile_into(BaseStrategy(), _colony_info())
        for rules in (
            parent.gain_priority,
            parent.action_priority,
            parent.treasure_priority,
            parent.trash_priority,
        ):
            for rule in rules:
                rule._fired = not (
                    rule.card_name == "Platinum"
                    and rules is parent.gain_priority
                )

        prune_unfired_rules(parent, min_rules=0)
        synchronize_strategic_genome(parent, _colony_info())
        child = crossover_strategic_strategies(
            parent, parent, _colony_info()
        )

        assert child is not None
        assert child._strategic_genome.economy.prefer_platinum is False
        assert all(rule.card_name != "Platinum" for rule in child.gain_priority)

    def test_surviving_pileout_does_not_mask_pruned_estate_greening(self):
        genome = StrategicGenome(
            greening=GreeningPlan(
                duchy_mode="never", estate_mode="threshold", estate_threshold=2
            ),
            endgame=EndgamePlan(estate_pileout=True),
            treasure_order=["Gold", "Silver", "Copper"],
        )
        parent = genome.compile_into(BaseStrategy(), _info())
        parent.gain_priority = [
            rule
            for rule in parent.gain_priority
            if not (
                rule.card_name == "Estate"
                and "provinces_left" in getattr(rule.condition, "_source", "")
            )
        ]

        synchronize_strategic_genome(parent, _info())
        child = crossover_strategic_strategies(parent, parent, _info())

        assert child is not None
        assert child._strategic_genome.greening.estate_mode == "never"
        assert child._strategic_genome.endgame.estate_pileout is True
        estate_sources = [
            getattr(rule.condition, "_source", "")
            for rule in child.gain_priority
            if rule.card_name == "Estate"
        ]
        assert len(estate_sources) == 1
        assert "empty_piles" in estate_sources[0]


class TestMutateMenu:
    def test_invariants_survive_heavy_mutation(self):
        random.seed(8)
        info = _info()
        s = random_menu_strategy(info)
        state, player = _mock_state(), _mock_player()
        for _ in range(200):
            s = mutate_menu(s, info, rate=1.0)
            s = normalize_menu(s, info)
            names = [r.card_name for r in s.gain_priority]
            assert "Province" in names
            assert "Curse" not in names
            for rule in s.gain_priority:
                if rule.condition is not None:
                    assert isinstance(bool(rule.condition(state, player)), bool)

    def test_cap_adjustment_changes_cap_value(self):
        random.seed(9)
        info = _info()
        s = BaseStrategy()
        s.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 2)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
        ]
        s.action_priority = [PriorityRule("Smithy")]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        s.trash_priority = []

        seen_caps = set()
        for _ in range(120):
            mutate_menu(s, info, rate=1.0)
            for rule in s.gain_priority:
                if rule.card_name == "Smithy" and rule.condition is not None:
                    src = getattr(rule.condition, "_source", "")
                    if "max_in_deck" in src:
                        seen_caps.add(src)
        assert len(seen_caps) > 1, f"cap never changed: {seen_caps}"

    def test_mutation_can_add_missing_kingdom_pick(self):
        random.seed(10)
        info = _info()
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold"), PriorityRule("Silver")]
        s.action_priority = []
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        s.trash_priority = []

        for _ in range(100):
            mutate_menu(s, info, rate=1.0)
            if any(r.card_name in KINGDOM for r in s.gain_priority):
                break
        assert any(r.card_name in KINGDOM for r in s.gain_priority)


class TestNormalizeMenu:
    def test_reinserts_province(self):
        info = _info()
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Gold"), PriorityRule("Silver")]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        assert s.gain_priority[0].card_name == "Province"

    def test_dedupes_identical_rules(self):
        info = _info()
        cond = PriorityRule.max_in_deck("Smithy", 2)
        s = BaseStrategy()
        s.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Smithy", cond),
            PriorityRule("Smithy", cond),
            PriorityRule("Gold"),
            PriorityRule("Gold"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        names = [(r.card_name, getattr(r.condition, "_source", None)) for r in s.gain_priority]
        assert len(names) == len(set(names))

    def test_drops_curse_and_unconditional_copper(self):
        info = _info()
        s = BaseStrategy()
        s.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Curse"),
            PriorityRule("Copper"),
            PriorityRule("Copper", PriorityRule.provinces_left("<=", 1)),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        names = [r.card_name for r in s.gain_priority]
        assert "Curse" not in names
        # The gated Copper rule survives; the unconditional one is dropped.
        coppers = [r for r in s.gain_priority if r.card_name == "Copper"]
        assert len(coppers) == 1 and coppers[0].condition is not None

    def test_reinserts_colony_on_colony_boards(self):
        info = _colony_info()
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold"), PriorityRule("Silver")]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        assert s.gain_priority[0].card_name == "Colony"
        # Platinum is restored to treasure_priority, ahead of Gold.
        treasures = [r.card_name for r in s.treasure_priority]
        assert treasures.index("Platinum") < treasures.index("Gold")

    def test_moves_province_above_unconditional_gold(self):
        info = _info()
        s = BaseStrategy()
        s.gain_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Province"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        names = [r.card_name for r in s.gain_priority]
        assert names.index("Province") < names.index("Gold")

    def test_moves_colony_and_province_above_unconditional_treasures(self):
        info = _colony_info()
        s = BaseStrategy()
        s.gain_priority = [
            PriorityRule("Gold"),
            PriorityRule("Province"),
            PriorityRule("Colony"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        names = [r.card_name for r in s.gain_priority]
        # Composition: Colony must lead — an unconditional Province above it
        # would shadow Colony at $11+ just like the Gold shadowed both.
        assert names == ["Colony", "Province", "Gold"]

    def test_moves_colony_above_unconditional_province(self):
        info = _colony_info()
        s = BaseStrategy()
        s.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Colony"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        names = [r.card_name for r in s.gain_priority]
        assert names == ["Colony", "Province"]

    def test_leaves_gated_province_above_colony(self):
        info = _colony_info()
        gated_province = PriorityRule("Province", PriorityRule.provinces_left("<=", 4))
        s = BaseStrategy()
        s.gain_priority = [gated_province, PriorityRule("Colony")]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        names = [(r.card_name, r.condition is not None) for r in s.gain_priority]
        # A gated Province above Colony is legitimate strategy space — untouched.
        assert names == [("Province", True), ("Colony", False)]

    def test_leaves_capped_pick_and_gated_gold_above_province(self):
        info = _info()
        capped_pick = PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 3))
        gated_gold = PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 4))
        s = BaseStrategy()
        s.gain_priority = [capped_pick, gated_gold, PriorityRule("Province"), PriorityRule("Silver", PriorityRule.turn_number("<=", 10))]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        normalize_menu(s, info)
        names = [r.card_name for r in s.gain_priority]
        # Gated rules above Province are legitimate strategy space — untouched.
        assert names == ["Smithy", "Gold", "Province", "Silver"]

    def test_ensures_basic_treasures_playable(self):
        info = _info()
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province")]
        s.treasure_priority = [PriorityRule("Gold")]
        normalize_menu(s, info)
        names = [r.card_name for r in s.treasure_priority]
        assert "Silver" in names and "Copper" in names

    def test_repairs_unconditional_action_order_by_role(self):
        info = KingdomInfo.from_kingdom(["Watchtower", "Peddler", "Workers' Village"])
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Watchtower"),
            PriorityRule("Peddler"),
            PriorityRule("Workers' Village"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        assert [r.card_name for r in s.action_priority] == [
            "Workers' Village",
            "Peddler",
            "Watchtower",
        ]

    def test_off_board_cantrip_keeps_priority_over_kingdom_terminal(self):
        # Horse is a +1 Action cantrip gained off the board (Livery, etc.) and
        # is not in the kingdom; it must still rank ahead of a kingdom terminal
        # draw rather than being sunk to last as an unknown card.
        info = KingdomInfo.from_kingdom(["Smithy", "Livery"])
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [PriorityRule("Horse"), PriorityRule("Smithy")]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        assert [r.card_name for r in s.action_priority] == ["Horse", "Smithy"]

    def test_command_rule_stays_before_its_payload(self):
        # Daimyo is a pending-replay Command: it registers a slot that fires on
        # the next non-Command Action played from hand, so the seed deliberately
        # plays the Command before its payload (Smithy). The role sort treats
        # the Command as a terminal and must not sink it below the terminal
        # draw it is meant to replay, or a one-action hand strands the Command.
        info = KingdomInfo.from_kingdom(
            ["Daimyo", "Witch", "Village", "Smithy"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Daimyo"),
            PriorityRule("Smithy"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        assert [r.card_name for r in s.action_priority] == [
            "Daimyo",
            "Smithy",
        ]

    def test_supply_command_does_not_pin_following_cantrip(self):
        # Band of Misfits is a *supply-targeting* Command: it plays a cheaper
        # non-Command Action from the supply immediately on play, so it never
        # consumes the next Action played from hand. The rule after it is not a
        # payload that must wait, so the role-order repair must still float the
        # cantrip ahead of the Command-as-terminal. The Command itself stays
        # pinned (it is still treated as a terminal anchor) and Peddler reflows
        # into the freed slot ahead of it.
        info = KingdomInfo.from_kingdom(
            ["Band of Misfits", "Watchtower", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Band of Misfits"),
            PriorityRule("Watchtower"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        # Peddler (a cantrip) must not be stranded behind Watchtower just because
        # a supply-targeting Command sits at the front.
        assert names.index("Peddler") < names.index("Watchtower")

    def test_conclave_does_not_pin_following_terminal(self):
        # Conclave plays an Action from hand, but it picks that target by card
        # stats (BaseAI.choose_action_to_play_with_conclave), not by
        # action_priority order, and it is only an option when Conclave is
        # actually drawn. Pinning the rule after Conclave would strand cantrips
        # whenever Conclave is absent, so Conclave must stay a plain terminal
        # anchor with no pinned payload and the role sort must still float the
        # cantrip ahead of the following kingdom terminal.
        info = KingdomInfo.from_kingdom(["Conclave", "Watchtower", "Peddler"])
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Conclave"),
            PriorityRule("Watchtower"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        # Peddler (a cantrip) must not be stranded behind Watchtower just because
        # Conclave (a terminal hand-action player) sits at the front.
        assert names.index("Peddler") < names.index("Watchtower")

    def test_pending_command_pins_payload_past_intervening_command(self):
        # A pending-replay Command's slot fires on the next *non-Command* Action
        # played from hand, so an intervening Command (Band of Misfits) does not
        # satisfy it. The real payload (Smithy) must stay pinned ahead of the
        # unrelated Peddler cantrip; pinning only the immediate next rule (the
        # supply Command) would let the role sort sink Smithy behind Peddler.
        info = KingdomInfo.from_kingdom(
            ["Daimyo", "Band of Misfits", "Smithy", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Daimyo"),
            PriorityRule("Band of Misfits"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        # Daimyo and Band of Misfits stay pinned as terminal anchors at the front;
        # Smithy stays pinned as Daimyo's payload ahead of the Peddler cantrip.
        assert names[0] == "Daimyo"
        assert names[1] == "Band of Misfits"
        assert names.index("Smithy") < names.index("Peddler")

    def test_nested_pending_commands_keep_payload_order(self):
        # Two pending-replay Commands in a row (Daimyo, Flagship) each pin their
        # payload. Flagship is a Command so it is skipped as Daimyo's payload
        # target; Smithy (the first non-Command Action) is pinned. Every rule
        # stays in place.
        info = KingdomInfo.from_kingdom(
            ["Daimyo", "Flagship", "Smithy", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Daimyo"),
            PriorityRule("Flagship"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names == ["Daimyo", "Flagship", "Smithy", "Peddler"]

    def test_gated_pending_command_pins_payload(self):
        # A *gated* pending-replay Command (play Daimyo only under a condition)
        # still registers the pending-replay slot whenever the gate passes, so
        # its payload (Smithy) must stay pinned ahead of an unrelated cantrip.
        # The gate only decides whether the Command plays; it does not change
        # which Action the slot fires on. Without pinning the payload here, the
        # role sort floats Peddler ahead of Smithy and the replay lands on the
        # wrong card.
        info = KingdomInfo.from_kingdom(
            ["Daimyo", "Witch", "Smithy", "Peddler"]
        )
        gate = PriorityRule.provinces_left(">", 2)
        gated_daimyo = PriorityRule("Daimyo", gate)
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            gated_daimyo,
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        # The gated Daimyo stays pinned at its slot, and Smithy stays pinned as
        # its payload ahead of the Peddler cantrip.
        assert s.action_priority[0] is gated_daimyo
        assert names.index("Smithy") < names.index("Peddler")

    def test_pending_command_pins_payload_past_gated_command(self):
        # Finding A: a *gated* intervening Command must also be skipped when
        # locating a pending-replay Command's payload. A Command is ``is_command``
        # regardless of its gate, so Band of Misfits(gate) never satisfies
        # Daimyo's pending-replay slot; whenever the gate is false the slot fires
        # on the next non-Command Action. Smithy is that payload and must stay
        # pinned ahead of the unrelated Peddler cantrip. Band of Misfits stays in
        # place as its own (gated) anchor.
        info = KingdomInfo.from_kingdom(
            ["Daimyo", "Band of Misfits", "Smithy", "Peddler"]
        )
        gate = PriorityRule.provinces_left(">", 2)
        gated_bom = PriorityRule("Band of Misfits", gate)
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Daimyo"),
            gated_bom,
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Daimyo"
        assert s.action_priority[1] is gated_bom
        assert names.index("Smithy") < names.index("Peddler")

    def test_throne_room_pins_following_payload(self):
        # Finding B: Throne Room is a play-an-Action multiplier — on play it asks
        # the AI to choose an Action *from hand* and plays it twice
        # (cards/base_set/throne_room.py). If the role sort floats the cantrip
        # ahead of Throne Room, the payload (Smithy) leaves hand before Throne
        # Room can call choose_action on it, so the multiplier fizzles. Smithy
        # must stay pinned immediately after Throne Room, ahead of Peddler.
        info = KingdomInfo.from_kingdom(
            ["Throne Room", "Smithy", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Throne Room"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Throne Room"
        assert names.index("Smithy") < names.index("Peddler")

    def test_kings_court_pins_following_payload(self):
        # King's Court is the same play-an-Action multiplier family (plays a
        # chosen hand Action three times, cards/prosperity/kings_court.py); its
        # payload must stay pinned immediately after it.
        info = KingdomInfo.from_kingdom(
            ["King's Court", "Smithy", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("King's Court"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "King's Court"
        assert names.index("Smithy") < names.index("Peddler")

    def test_shop_pins_following_payload(self):
        # Finding A: Shop is a one-shot "play an Action from hand" card — on play
        # it asks the AI to choose an Action from hand and plays it
        # (cards/cornucopia/shop.py). Detection now covers the whole hand-action
        # consumer category, not just the multipliers, so [Shop, Smithy] must
        # keep Smithy pinned immediately after Shop rather than letting the role
        # sort float the cantrip ahead and strand Shop's payload.
        info = KingdomInfo.from_kingdom(
            ["Shop", "Smithy", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Shop"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Shop"
        assert names.index("Smithy") < names.index("Peddler")

    def test_royal_galley_and_specialist_pin_following_payload(self):
        # Royal Galley plays an Action from hand (cards/allies/standalone.py) and
        # Specialist replays-or-gains a chosen hand Action (same file). Both are
        # hand-action consumers, so each keeps its Smithy payload pinned ahead of
        # the Peddler cantrip.
        for consumer in ("Royal Galley", "Specialist"):
            info = KingdomInfo.from_kingdom([consumer, "Smithy", "Peddler"])
            s = BaseStrategy()
            s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
            s.action_priority = [
                PriorityRule(consumer),
                PriorityRule("Smithy"),
                PriorityRule("Peddler"),
            ]
            s.treasure_priority = [
                PriorityRule("Gold"),
                PriorityRule("Silver"),
                PriorityRule("Copper"),
            ]

            normalize_menu(s, info)

            names = [r.card_name for r in s.action_priority]
            assert names[0] == consumer
            assert names.index("Smithy") < names.index("Peddler")

    def test_disciple_and_prince_do_not_pin_following_terminal(self):
        # Disciple and Prince use card-specific choosers that do not consult
        # action_priority, so the rule after them is not a priority payload. The
        # role sort must remain free to float safer actions ahead of terminals.
        cases = [
            ("Disciple", "Smithy", "Peddler"),
            ("Prince", "Smithy", "Village"),
        ]
        for consumer, terminal, safer_action in cases:
            info = KingdomInfo.from_kingdom([consumer, terminal, safer_action])
            s = BaseStrategy()
            s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
            s.action_priority = [
                PriorityRule(consumer),
                PriorityRule(terminal),
                PriorityRule(safer_action),
            ]
            s.treasure_priority = [
                PriorityRule("Gold"),
                PriorityRule("Silver"),
                PriorityRule("Copper"),
            ]

            normalize_menu(s, info)

            names = [r.card_name for r in s.action_priority]
            assert names.index(safer_action) < names.index(terminal)

    def test_non_priority_trashers_do_not_pin_following_terminal(self):
        # Death Cart and Graverobber choose trash targets through card-specific
        # trash hooks, not action_priority. The rule after them is therefore
        # not a priority payload; safer actions must remain free to role-sort
        # ahead of following terminals when the trasher is absent or takes a
        # different mode.
        cases = [
            ("Death Cart", "Smithy", "Peddler"),
            ("Graverobber", "Smithy", "Peddler"),
        ]
        for trasher, terminal, safer_action in cases:
            info = KingdomInfo.from_kingdom([trasher, terminal, safer_action])
            s = BaseStrategy()
            s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
            s.action_priority = [
                PriorityRule(trasher),
                PriorityRule(terminal),
                PriorityRule(safer_action),
            ]
            s.treasure_priority = [
                PriorityRule("Gold"),
                PriorityRule("Silver"),
                PriorityRule("Copper"),
            ]

            normalize_menu(s, info)

            names = [r.card_name for r in s.action_priority]
            assert names.index(safer_action) < names.index(terminal)

    def test_overlord_is_command_anchor_without_payload_pin(self):
        # Overlord plays a target from the supply like Band of Misfits/Captain,
        # so it must be anchored as a Command but must not pin the following
        # action-priority rule as a hand payload.
        info = KingdomInfo.from_kingdom(["Overlord", "Smithy", "Peddler"])
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Overlord"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert get_card("Overlord").is_command
        assert names[0] == "Overlord"
        assert names.index("Peddler") < names.index("Smithy")

    def test_elder_pins_following_payload(self):
        # Finding A: Elder chooses an Action from hand via choose_action and
        # plays it indirectly (cards/allies/townsfolk.py:237-256), so it is a
        # hand-action consumer. On [Elder, Smithy, Peddler] the role sort would
        # otherwise float the Peddler cantrip ahead of the terminal Smithy, so
        # Elder's choose_action would pick Peddler instead of the intended
        # Smithy. Smithy must stay pinned immediately after Elder.
        info = KingdomInfo.from_kingdom(["Elder", "Smithy", "Peddler"])
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Elder"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Elder"
        assert names.index("Smithy") < names.index("Peddler")

    def test_farmhands_pins_non_duration_payload(self):
        # Farmhands' next-turn play filters to non-Duration Actions and uses
        # choose_action, so it skips an intervening Duration while pinning the
        # first eligible unconditional fallback payload.
        info = KingdomInfo.from_kingdom(["Farmhands", "Wharf", "Smithy", "Peddler"])
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Farmhands"),
            PriorityRule("Wharf"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Farmhands"
        assert names.index("Smithy") < names.index("Peddler")

    def test_procession_skips_ineligible_duration_payload(self):
        # Finding B: Procession plays a *non-Duration* Action from hand twice
        # then trashes it (cards/dark_ages/procession.py:20), so its chooser
        # filters out Durations. On [Procession, Wharf, Smithy, Peddler] the pin
        # scan must skip the ineligible Duration Wharf and pin the first eligible
        # non-Duration Action (Smithy) as Procession's payload — otherwise Smithy
        # stays movable and the role sort floats Peddler ahead, so Procession's
        # choose_action takes Peddler instead of the intended Smithy. The skipped
        # Wharf is pinned in its slot so the cantrip cannot reflow ahead of the
        # payload.
        info = KingdomInfo.from_kingdom(
            ["Procession", "Wharf", "Smithy", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Procession"),
            PriorityRule("Wharf"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Procession"
        # Smithy is the pinned non-Duration payload and stays ahead of Peddler.
        assert names.index("Smithy") < names.index("Peddler")

    def test_royal_galley_skips_ineligible_duration_payload(self):
        # Royal Galley sets aside a *non-Duration* Action to replay
        # (cards/allies/standalone.py:353), so like Procession it must skip the
        # ineligible Duration Wharf and pin Smithy as its payload.
        info = KingdomInfo.from_kingdom(
            ["Royal Galley", "Wharf", "Smithy", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Royal Galley"),
            PriorityRule("Wharf"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Royal Galley"
        assert names.index("Smithy") < names.index("Peddler")

    def test_duration_allowing_consumer_pins_following_duration(self):
        # Guard against over-restriction: Throne Room's chooser does NOT exclude
        # Durations (cards/base_set/throne_room.py), so on
        # [Throne Room, Wharf, Peddler] the immediately-following Duration Wharf
        # IS Throne Room's intended payload and must stay pinned right after it,
        # ahead of the Peddler cantrip. Only _NON_DURATION_CONSUMERS skip
        # Durations.
        info = KingdomInfo.from_kingdom(
            ["Throne Room", "Wharf", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Throne Room"),
            PriorityRule("Wharf"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Throne Room"
        assert names.index("Wharf") < names.index("Peddler")

    def test_throne_room_pins_immediate_command_payload(self):
        # Round 9: an immediate hand-action consumer (Throne Room) chooses its
        # target from hand on play, accepting ANY eligible card.is_action —
        # including a Command (cards/base_set/throne_room.py accepts every
        # card.is_action; choose_action then follows action_priority). So on
        # [Throne Room, Band of Misfits, Watchtower, Peddler] the payload is the
        # immediately-following Command Band of Misfits, which must NOT be
        # skipped: it stays pinned right after Throne Room. The Command skip is
        # reserved for pending-replay Commands.
        #
        # Band of Misfits is a *supply* Command (not a pending-replay/consumer),
        # so it pins no payload of its own. This discriminates old vs new: under
        # the old skip-every-Command logic Throne Room would skip Band of Misfits
        # and pin Watchtower as its payload, keeping the terminal Watchtower
        # pinned ahead of the Peddler cantrip. Under the fix Throne Room pins
        # Band of Misfits (its real immediate payload), leaving Watchtower and
        # Peddler free to role-sort — so the cantrip Peddler correctly sorts
        # ahead of the terminal Watchtower.
        info = KingdomInfo.from_kingdom(
            ["Throne Room", "Band of Misfits", "Watchtower", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Throne Room"),
            PriorityRule("Band of Misfits"),
            PriorityRule("Watchtower"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        # Band of Misfits is Throne Room's immediate eligible payload — pinned
        # right after it, NOT skipped to Watchtower.
        assert names[0] == "Throne Room"
        assert names[1] == "Band of Misfits"
        # Watchtower was NOT pinned as Throne Room's payload, so the role sort is
        # free to float the Peddler cantrip ahead of the Watchtower terminal.
        assert names.index("Peddler") < names.index("Watchtower")

    def test_consumer_pins_unconditional_fallback_after_gated_candidate(self):
        # If the first eligible candidate after a consumer is gated, choose_action
        # can fall through to the next eligible rule when the gate is false. The
        # scan must keep the gated rule anchored and also pin the unconditional
        # fallback payload ahead of unrelated cantrips.
        info = KingdomInfo.from_kingdom(["Throne Room", "Watchtower", "Smithy", "Peddler"])
        gated_watchtower = PriorityRule("Watchtower", PriorityRule.actions_in_hand(">=", 2))
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Throne Room"),
            gated_watchtower,
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Throne Room"
        assert s.action_priority[1] is gated_watchtower
        assert names.index("Smithy") < names.index("Peddler")

    def test_pending_command_skips_command_immediate_consumer_does_not(self):
        # Round 9 contrast: a pending-replay Command (Daimyo) fires only on the
        # next *non-Command* Action, so it DOES skip an intervening Command
        # (Band of Misfits) to reach its non-Command payload (Smithy) — the
        # round-4 behavior. This is the opposite of an immediate consumer like
        # Throne Room, which would have pinned the Command itself.
        info = KingdomInfo.from_kingdom(
            ["Daimyo", "Band of Misfits", "Smithy", "Peddler"]
        )
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [
            PriorityRule("Daimyo"),
            PriorityRule("Band of Misfits"),
            PriorityRule("Smithy"),
            PriorityRule("Peddler"),
        ]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        names = [r.card_name for r in s.action_priority]
        assert names[0] == "Daimyo"
        assert names[1] == "Band of Misfits"
        # The intervening Command is skipped; Smithy is the pinned payload.
        assert names.index("Smithy") < names.index("Peddler")

    def test_leaves_gated_action_rules_in_place(self):
        info = KingdomInfo.from_kingdom(["Watchtower", "Peddler"])
        gated_watchtower = PriorityRule("Watchtower", PriorityRule.actions_in_hand(">=", 2))
        s = BaseStrategy()
        s.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        s.action_priority = [gated_watchtower, PriorityRule("Peddler")]
        s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        normalize_menu(s, info)

        assert s.action_priority[0] is gated_watchtower
        assert [r.card_name for r in s.action_priority] == ["Watchtower", "Peddler"]


class TestKingdomSimilarity:
    def _menu(self, *kingdom_picks: str) -> BaseStrategy:
        s = BaseStrategy()
        s.gain_priority = (
            [PriorityRule("Province"), PriorityRule("Duchy"), PriorityRule("Gold")]
            + [PriorityRule(c) for c in kingdom_picks]
            + [PriorityRule("Silver")]
        )
        return s

    def test_shared_skeleton_does_not_count(self):
        a = self._menu("Witch", "Chapel")
        b = self._menu("Smithy", "Village")
        assert kingdom_similarity(a, b) == 0.0

    def test_identical_picks_score_one(self):
        a = self._menu("Witch", "Chapel")
        b = self._menu("Witch", "Chapel")
        assert kingdom_similarity(a, b) == 1.0

    def test_pure_big_money_menus_share_a_niche(self):
        a = self._menu()
        b = self._menu()
        assert kingdom_similarity(a, b) == 1.0


class TestTrainerIntegration:
    def test_structured_is_default_and_produces_menus(self):
        trainer = GeneticTrainer(KINGDOM, population_size=1, generations=1)
        assert trainer.structured_genome is True
        random.seed(11)
        s = trainer.create_random_strategy()
        names = [r.card_name for r in s.gain_priority]
        assert "Province" in names
        assert names.index("Province") <= 3
        assert hasattr(s, "_strategic_genome")
        assert "Copper" not in names

    def test_legacy_flag_restores_freeform_init(self):
        trainer = GeneticTrainer(
            KINGDOM, population_size=1, generations=1, structured_genome=False
        )
        # Legacy mode skips structured-genome setup entirely.
        assert trainer._kingdom_info is None
        random.seed(12)
        # Legacy init shuffles all cards including Copper into the gain list.
        seen_copper = any(
            any(r.card_name == "Copper" for r in trainer.create_random_strategy().gain_priority)
            for _ in range(20)
        )
        assert seen_copper

    def test_representable_legacy_parent_is_promoted_for_semantic_crossover(self):
        trainer = GeneticTrainer(KINGDOM, population_size=1, generations=1)
        typed = trainer.create_random_strategy()
        legacy = BaseStrategy()
        legacy.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        legacy.treasure_priority = [
            PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")
        ]

        child = trainer._crossover(typed, legacy)

        assert hasattr(child, "_strategic_genome")

    def test_unrepresentable_legacy_parent_keeps_compatibility_crossover(self):
        trainer = GeneticTrainer(KINGDOM, population_size=1, generations=1)
        typed = trainer.create_random_strategy()
        legacy = BaseStrategy()
        legacy.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        legacy.action_priority = [
            PriorityRule("Smithy", PriorityRule.turn_number("<=", 8))
        ]
        legacy.treasure_priority = [
            PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")
        ]

        child = trainer._crossover(typed, legacy)

        assert not hasattr(child, "_strategic_genome")

    def test_structured_mutation_preserves_invariants(self):
        trainer = GeneticTrainer(KINGDOM, population_size=1, generations=1, mutation_rate=1.0)
        random.seed(13)
        s = trainer.create_random_strategy()
        for _ in range(50):
            s = trainer._mutate(s)
            s = trainer._normalize(s)
        names = [r.card_name for r in s.gain_priority]
        assert "Province" in names
        assert "Curse" not in names

    def test_structured_crossover_children_are_normalized(self):
        trainer = GeneticTrainer(KINGDOM, population_size=4, generations=1)
        random.seed(14)
        pop = [trainer.create_random_strategy() for _ in range(4)]
        next_pop = trainer.create_next_generation(pop, [50.0, 40.0, 30.0, 20.0])
        for s in next_pop:
            keys = [
                (r.card_name, getattr(r.condition, "_source", None) if r.condition else None)
                for r in s.gain_priority
            ]
            assert len(keys) == len(set(keys)), f"duplicate rules survived: {keys}"
            assert any(r.card_name == "Province" for r in s.gain_priority)


class TestWidenedGreeningVocabulary:
    """The greening-gate vocabulary must include the shapes that classic
    archetypes need: an ungated Duchy (Rebuild-style "Duchy over Gold"),
    pile-pressure Estates, and a cap-1 early-turn opener gate for picks
    (Chapel-style openings). See docs/calibration.md — the rebuild_duchy
    board exposed that these were unrepresentable."""

    def test_duchy_gate_can_be_ungated_but_usually_is_not(self):
        from dominion.simulation.structured_genome import _greening_gate

        rng = random.Random(0)
        gates = [_greening_gate("Duchy", rng) for _ in range(400)]
        ungated = sum(1 for gate in gates if gate is None)
        assert ungated > 0, "ungated Duchy never offered — Rebuild-style rushes stay unsearchable"
        assert ungated < 200, "ungated Duchy should stay a minority option"
        for gate in gates:
            if gate is not None:
                assert "provinces_left" in gate._source

    def test_estate_gate_includes_pile_pressure_option(self):
        from dominion.simulation.structured_genome import _greening_gate

        rng = random.Random(1)
        sources = [_greening_gate("Estate", rng)._source for _ in range(400)]
        assert any("empty_piles" in s for s in sources), "no pile-pressure Estate gate offered"
        assert any("provinces_left" in s for s in sources)

    def test_pick_gate_includes_opening_buy_shape(self):
        import re as _re

        from dominion.simulation.structured_genome import _pick_gate

        rng = random.Random(2)
        info = _info()
        opener = _re.compile(r"max_in_deck\('Chapel', 1\).*turn_number\('<=', ([2-4])\)")
        sources = [_pick_gate("Chapel", info, rng)._source for _ in range(400)]
        assert any(opener.search(s) for s in sources), (
            "no opener-shaped gate (cap 1 + turn <= 2-4) in 400 draws"
        )

    def test_mutation_can_discover_ungated_duchy(self):
        random.seed(7)
        info = _info()
        strategy = random_menu_strategy(info)
        found = False
        for _ in range(300):
            if not any(r.card_name == "Duchy" for r in strategy.gain_priority):
                strategy.gain_priority.insert(
                    1, PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4))
                )
            strategy = normalize_menu(mutate_menu(strategy, info, rate=0.9), info)
            duchy = next((r for r in strategy.gain_priority if r.card_name == "Duchy"), None)
            if duchy is not None and duchy.condition is None:
                found = True
                break
        assert found, "re-gate mutation never produced an ungated Duchy"
