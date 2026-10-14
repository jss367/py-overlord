"""Policy genes retain behavior through operators, exports and discovery."""

from copy import deepcopy
import importlib.util
import random

import cloudpickle
import pytest

from dominion.analysis.strategy_library import referenced_cards
from dominion.simulation.adversarial_league import genome_signature
from dominion.simulation.structured_genome import KingdomInfo, mutate_menu, normalize_menu
from dominion.simulation.strategic_genome import StrategicGenome, crossover_strategic_strategies, synchronize_strategic_genome
from dominion.strategy.card_policies import validate_policies, investment_points
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.genome_simplification import simplify_strategy
from dominion.strategy.strategies.base_strategy import BaseStrategy
from tests.test_shared_card_tactics import make_state
from scripts.league_evolve import _describe

INFO = KingdomInfo.from_kingdom(['Watchtower','Clerk','Investment','Bounty Hunter','Sheepdog','Sleigh'])
SETTINGS = {'watchtower':{'terminal_limit':2}, 'investment':{'min_names':2},
            'bounty_hunter':{'prefer_new_name':True,'buy_breakpoint':8}}


@pytest.mark.parametrize('settings', [None, {}, SETTINGS])
def test_typed_conversion_pickle_normalization_and_discovery(settings):
    genome = StrategicGenome(card_decision_policies=deepcopy(settings))
    strategy = genome.compile_into(BaseStrategy(), INFO)
    restored = cloudpickle.loads(cloudpickle.dumps(genome)).compile_into(BaseStrategy(), INFO)
    assert restored.card_decision_policies == settings
    assert restored.card_decision_policies is not settings or settings is None
    clone = cloudpickle.loads(cloudpickle.dumps(strategy))
    normalize_menu(clone, INFO)
    clone = simplify_strategy(clone)
    synchronize_strategic_genome(clone, INFO)
    clone._strategic_genome.compile_into(clone, INFO)
    assert clone.card_decision_policies == settings
    assert _describe(clone)['card_decision_policies'] == settings
    if settings:
        assert {'Watchtower','Investment','Bounty Hunter'} <= referenced_cards(clone)


def test_none_and_explicit_empty_have_distinct_deduplication_identity():
    a,b = BaseStrategy(),BaseStrategy()
    b.card_decision_policies = {}
    assert genome_signature(a) != genome_signature(b)


@pytest.mark.parametrize('family,values', [
    ('investment',{'min_names':99}), ('clerk',{'play_at_start':1}),
    ('unknown',{}), ('watchtower',{'unknown':True}),
])
def test_invalid_loaded_policy_is_rejected(family, values):
    with pytest.raises(ValueError):
        validate_policies({family:values})


def test_structured_mutation_changes_actual_parameters_and_keeps_genome_current():
    strategy = StrategicGenome().compile_into(BaseStrategy(),INFO)
    rng = random.Random(713)
    for _ in range(80):
        mutate_menu(strategy, INFO, 1.0, rng)
    settings = strategy.card_decision_policies
    assert settings
    validate_policies(settings)
    assert strategy._strategic_genome.card_decision_policies == settings
    assert any(name in settings for name in ('watchtower','investment','bounty_hunter','clerk','gain_order'))


@pytest.mark.parametrize('first', [None, {}, SETTINGS])
@pytest.mark.parametrize('second', [None, {}, SETTINGS])
def test_crossover_preserves_whole_settings_without_aliasing(first, second):
    a = StrategicGenome(card_decision_policies=deepcopy(first)).compile_into(BaseStrategy(),INFO)
    b = StrategicGenome(card_decision_policies=deepcopy(second)).compile_into(BaseStrategy(),INFO)
    child = crossover_strategic_strategies(a,b,INFO,random.Random(2))
    assert child.card_decision_policies in (first, second)
    assert child._strategic_genome.card_decision_policies == child.card_decision_policies
    if child.card_decision_policies is not None:
        assert child.card_decision_policies is not a.card_decision_policies
        assert child.card_decision_policies is not b.card_decision_policies


def test_configured_clerk_and_watchtower_hooks_change_behavior_but_callable_wins():
    strategy = EnhancedStrategy()
    state, player = make_state(strategy)
    strategy.card_decision_policies = {'clerk': {'dead_cards_first':True,'play_at_start':False},
                                       'watchtower':{'keep_copper_below_income':5}}
    player.hand = [get_card('Silver')]
    player.deck = []
    assert strategy.choose_watchtower_reaction(state,player,get_card('Copper')) is None
    assert not strategy.should_play_clerk_reaction(state,player)
    assert strategy.choose_card_to_topdeck_for_clerk(state,player,[get_card('Copper'),get_card('Province')]).name == 'Province'
    strategy.choose_watchtower_reaction = lambda *args: 'trash'
    clone = cloudpickle.loads(cloudpickle.dumps(strategy))
    assert clone.choose_watchtower_reaction(state,player,get_card('Copper')) == 'trash'


def test_explicit_bounty_priority_wins_over_policy_parameters():
    strategy = EnhancedStrategy()
    strategy.card_decision_policies = {'bounty_hunter':{'prefer_new_name':True}}
    strategy.bounty_hunter_exile_priority = [PriorityRule('Copper')]
    state,player = make_state(strategy)
    assert strategy.choose_bounty_hunter_exile(state,player,[get_card('Copper'),get_card('Estate')]).name == 'Copper'


from dominion.cards.registry import get_card


@pytest.mark.parametrize('hand', [['Silver','Gold'], ['Investment','Investment','Silver','Gold']])
def test_investment_uses_actual_remaining_live_names_and_never_legacy_selector(hand):
    strategy = EnhancedStrategy()
    strategy.choose_treasure_to_trash_for_investment = lambda *args: pytest.fail('Not an engine decision')
    state,player = make_state(strategy)
    player.hand = [get_card(n) for n in hand]
    assert investment_points(state,player) == len(set(hand))
    assert strategy.choose_investment_mode(state,player,True) == ('trash' if len(set(hand)) >= 3 else 'coin')
    strategy.card_decision_policies = {'investment':{'min_names':2}}
    assert strategy.choose_investment_mode(state,player,True) == 'trash'
    assert strategy.choose_investment_mode(state,player,False) == 'coin'


def test_investment_live_treasure_names_and_buy_breakpoint_parameter():
    from dominion.projects.capitalism import Capitalism
    strategy = EnhancedStrategy()
    state,player = make_state(strategy)
    player.projects = [Capitalism()]
    player.hand = [get_card('Bridge'),get_card('Silver'),get_card('Gold')]
    assert investment_points(state,player) == 3
    strategy.card_decision_policies = {'investment': {'min_names':2,'preserve_buy_breakpoint':True}}
    player.coins = 1
    # Bridge 1 + Silver 2 + Gold 3 + existing 1 = $7; +$1 reaches Province.
    assert strategy.choose_investment_mode(state,player,True) == 'coin'


def test_exported_policy_loads_and_discovery_finds_its_card(tmp_path, monkeypatch):
    from dominion.runner import save_strategy_as_python
    strategy = BaseStrategy()
    strategy.name = 'Exported Card Policies'
    strategy.card_decision_policies = deepcopy(SETTINGS)
    monkeypatch.chdir(tmp_path)
    path = tmp_path / 'exported.py'
    save_strategy_as_python(strategy, path, clean_for_publication=False)
    spec = importlib.util.spec_from_file_location('exported_policy',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory = next(getattr(module,n) for n in dir(module) if n.startswith('create_'))
    clone = factory()
    assert clone.card_decision_policies == SETTINGS
    assert {'Investment','Watchtower','Bounty Hunter'} <= referenced_cards(clone)


def test_investment_preserves_ordinary_legacy_choices_but_counts_real_points():
    from itertools import combinations_with_replacement
    from scripts.evaluate_remaining_card_policies import legacy_mode
    strategy = EnhancedStrategy()
    state, player = make_state(strategy)
    for length in range(1,7):
        for names in combinations_with_replacement(['Copper','Silver','Gold','Investment'],length):
            player.hand = [get_card(n) for n in names]
            assert investment_points(state,player) == len(set(names))
            assert strategy.choose_investment_mode(state,player,True) == legacy_mode(strategy,state,player,True)
    player.hand = [get_card('Silver'),get_card('Silver'),get_card('Gold')]
    assert investment_points(state,player)==2
    assert strategy.choose_investment_mode(state,player,True)=='trash'
    strategy.card_decision_policies={'investment':{'duplicate_name_discount':False}}
    assert strategy.choose_investment_mode(state,player,True)=='coin'


def test_investment_scores_inheritance_capitalism_combination_through_physical_play():
    from dominion.projects.capitalism import Capitalism
    strategy=EnhancedStrategy()
    strategy.trash_priority=[PriorityRule('Curse')]
    state,player=make_state(strategy)
    player.projects=[Capitalism()]
    player.inherited_action_name='Bridge'
    investment=get_card('Investment')
    player.in_play=[investment]
    player.hand=[get_card(n) for n in ['Curse','Estate','Silver','Gold']]
    investment.play_effect(state)
    assert player.vp_tokens==3
    assert investment in state.trash


def test_direct_semantic_mutation_searches_card_parameters():
    from dominion.simulation.strategic_genome import mutate_strategic_strategy
    strategy=StrategicGenome().compile_into(BaseStrategy(),INFO)
    rng=random.Random(501)
    for _ in range(20):
        assert mutate_strategic_strategy(strategy,INFO,1.0,rng)
    assert strategy.card_decision_policies
    assert strategy._strategic_genome.card_decision_policies==strategy.card_decision_policies


@pytest.mark.parametrize('settings,expected', [
    (None, set()), ({}, set()), ({'watchtower': {}}, {'Watchtower'}),
    ({'investment': {'min_names': 2}}, {'Investment'}),
    ({'clerk': {'play_at_start': False}}, {'Clerk'}),
    ({'bounty_hunter': {'prefer_new_name': True}}, {'Bounty Hunter'}),
    ({'gain_order': {'first': 'sheepdog'}}, {'Sleigh', 'Sheepdog', 'Cargo Ship'}),
])
def test_automatic_battle_board_includes_policy_only_references(tmp_path, settings, expected):
    from dominion.simulation.strategy_battle import StrategyBattle
    ours, other = EnhancedStrategy(), EnhancedStrategy()
    ours.card_decision_policies = settings
    battle = StrategyBattle(log_folder=str(tmp_path))
    assert set(battle._determine_board_references(ours, other).kingdom_cards) == expected
    battle.kingdom_cards = ['Village']
    assert battle._determine_board_references(ours, other).kingdom_cards == ['Village']
