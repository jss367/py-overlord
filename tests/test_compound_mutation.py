"""Tests for compound (and_) condition generation in the genetic mutator."""

import importlib
import random
import sys
import types

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


def _make_mock_state(turn_number=5, provinces_left=8, empty_piles=0, players=None):
    state = types.SimpleNamespace()
    state.turn_number = turn_number
    state.supply = {"Province": provinces_left}
    state.empty_piles = empty_piles
    state.players = players if players is not None else []
    return state


def _make_mock_player(coins=3, actions=1, buys=1, vp=3, all_cards=None, in_play=None):
    player = types.SimpleNamespace()
    player.coins = coins
    player.actions = actions
    player.buys = buys
    player.hand = []
    player.in_play = in_play if in_play is not None else []
    player.count_in_deck = lambda card_name: 0
    cards = all_cards if all_cards is not None else []
    player.all_cards = lambda _cards=cards: list(_cards)
    player.get_victory_points = lambda _g=None, _vp=vp: _vp
    player.actions_gained_this_turn = 0
    player.cards_gained_this_turn = 0
    return player


class TestCompoundConditionGeneration:
    def test_compound_generator_returns_callable(self):
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Laboratory"],
            population_size=1, generations=1,
        )
        random.seed(42)
        for _ in range(50):
            cond = trainer._random_condition_with_compound()
            assert cond is None or callable(cond), f"Got {type(cond)}"

    def test_compound_generator_eventually_produces_compound(self):
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Laboratory", "Witch"],
            population_size=1, generations=1,
        )
        random.seed(0)
        compound_count = 0
        for _ in range(400):
            cond = trainer._random_condition_with_compound()
            if cond is None:
                continue
            src = getattr(cond, "_source", "")
            if "PriorityRule.and_(" in src and "PriorityRule.card_in_play(" in src:
                compound_count += 1
        assert compound_count > 0

    def test_compound_generator_falls_back_when_no_actions(self):
        trainer = GeneticTrainer(
            ["Village"],
            population_size=1, generations=1,
        )
        trainer._kingdom_action_cards = []
        random.seed(1)
        for _ in range(100):
            cond = trainer._random_condition_with_compound()
            if cond is None:
                continue
            src = getattr(cond, "_source", "")
            assert "card_in_play" not in src, src

    def test_compound_conditions_evaluate_safely(self):
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Laboratory"],
            population_size=1, generations=1,
        )
        random.seed(7)
        action_card = types.SimpleNamespace(name="Village", is_action=True)
        deck = [action_card, action_card, action_card]
        state = _make_mock_state()
        player = _make_mock_player(all_cards=deck, in_play=[action_card])
        for _ in range(200):
            cond = trainer._random_condition_with_compound()
            if cond is None:
                continue
            result = cond(state, player)
            assert isinstance(result, bool)

    def test_card_in_play_uses_kingdom_actions(self):
        kingdom = ["Village", "Smithy", "Market", "Laboratory"]
        trainer = GeneticTrainer(kingdom, population_size=1, generations=1)
        random.seed(123)
        compounds_seen = 0
        for _ in range(500):
            cond = trainer._random_condition_with_compound()
            if cond is None:
                continue
            src = getattr(cond, "_source", "")
            if "PriorityRule.card_in_play(" not in src:
                continue
            compounds_seen += 1
            start = src.index("PriorityRule.card_in_play(") + len("PriorityRule.card_in_play(")
            end = src.index(")", start)
            card_arg = src[start:end].strip().strip("'\"")
            assert card_arg in trainer._kingdom_action_cards
        assert compounds_seen > 0


class TestCompoundSerializationRoundTrip:
    def test_compound_round_trips(self, tmp_path):
        from runner import save_strategy_as_python
        strategy = BaseStrategy()
        strategy.name = "CompoundRoundTrip"
        compound_cond = PriorityRule.and_(
            PriorityRule.card_in_play("Village"),
            PriorityRule.resources("actions", "<", 2),
        )
        strategy.gain_priority = [
            PriorityRule("Smithy", compound_cond),
            PriorityRule("Province"),
        ]
        strategy.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]
        strategy.trash_priority = []
        out_file = tmp_path / "compound_strategy.py"
        save_strategy_as_python(strategy, out_file, "CompoundStrategy")
        source = out_file.read_text()
        assert "<lambda" not in source, source
        assert "<function" not in source, source
        assert "PriorityRule.and_(" in source, source
        assert "PriorityRule.card_in_play(" in source, source
        sys.path.insert(0, str(tmp_path))
        try:
            mod = importlib.import_module("compound_strategy")
            generated = mod.CompoundStrategy()
            assert generated.name == "CompoundRoundTrip"
            smithy_rule = generated.gain_priority[0]
            assert smithy_rule.condition is not None
            assert callable(smithy_rule.condition)
            village = types.SimpleNamespace(name="Village", is_action=True)
            state = _make_mock_state()
            player = _make_mock_player(actions=1, in_play=[village])
            assert smithy_rule.condition(state, player) is True
            player_empty = _make_mock_player(actions=1, in_play=[])
            assert smithy_rule.condition(state, player_empty) is False
        finally:
            sys.path.pop(0)
            sys.modules.pop("compound_strategy", None)


class TestMutateCanProduceCompound:
    def test_mutation_eventually_produces_compound_condition(self):
        from copy import deepcopy
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Laboratory", "Witch"],
            population_size=1, generations=1, mutation_rate=1.0,
        )
        seed = BaseStrategy()
        seed.name = "seed"
        seed.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
        ]
        seed.action_priority = [PriorityRule("Village"), PriorityRule("Smithy")]
        seed.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]
        seed.trash_priority = []
        random.seed(99)
        saw_compound = False
        for _ in range(200):
            mutated = trainer._mutate(deepcopy(seed))
            for lst in (mutated.gain_priority, mutated.action_priority):
                for rule in lst:
                    src = getattr(rule.condition, "_source", "") if rule.condition else ""
                    if "PriorityRule.and_(" in src and "card_in_play" in src:
                        saw_compound = True
                        break
                if saw_compound:
                    break
            if saw_compound:
                break
        assert saw_compound
