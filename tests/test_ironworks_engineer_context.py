"""Contextual gains preserve priorities while resolving physical card rules."""

import pytest

from dominion.ai.gain_context import FreeGainContext
from dominion.ai import tactical_defaults
from dominion.cards.registry import get_card
from dominion.projects.capitalism import Capitalism
from dominion.prophecies.registry import get_prophecy
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.phase_strategy import PhaseAwareStrategy, StrategyPhase
from tests.test_shared_card_tactics import make_state
from tests.test_committed_free_gain_recording import teacher_state, labels


@pytest.mark.parametrize("source", ["Ironworks", "Engineer"])
def test_independent_priorities_and_inherited_purchase_selection(source):
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    get_card(source).play_effect(state)
    assert player.discard[-1].name == "Village"
    strategy.free_gain_priority = [PriorityRule("Smithy")]
    get_card(source).play_effect(state)
    assert player.discard[-1].name == "Smithy"
    assert player.ai.choose_buy(state, [get_card("Village"), get_card("Smithy")]).name == "Village"


@pytest.mark.parametrize("source", ["Ironworks", "Engineer"])
def test_phase_purchase_priorities_are_inherited(source):
    strategy = PhaseAwareStrategy()
    strategy.phase_gain_priority[StrategyPhase.ENDGAME] = [PriorityRule("Village")]
    state, player = make_state(strategy)
    get_card(source).play_effect(state)
    assert player.discard[-1].name == "Village"


@pytest.mark.parametrize("source", ["Ironworks", "Engineer"])
@pytest.mark.parametrize("invalid", [None, "not a card", "Province"])
def test_invalid_contextual_overrides_still_gain_a_legal_card(source, invalid):
    strategy = EnhancedStrategy()
    strategy.choose_free_gain = lambda *args: get_card(invalid) if invalid == "Province" else invalid
    state, player = make_state(strategy)
    get_card(source).play_effect(state)
    assert [c.name for c in player.discard] == ["Smithy"]


@pytest.mark.parametrize("source", ["Ironworks", "Engineer"])
def test_component_costs_exposed_piles_and_physical_depletion(source):
    strategy = EnhancedStrategy()
    menus = []
    strategy.choose_free_gain = lambda s, p, choices, context: menus.append({c.name for c in choices}) or get_card("Acolyte")
    names = ("Herb Gatherer", "Acolyte", "Sorceress", "Sibyl", "Engineer", "Alchemist", "Horse", "Nobles", "Smithy")
    state, player = make_state(strategy, names)
    state.supply["Smithy"] = 0
    state.non_supply_pile_names.add("Horse")
    state.rotate_supply_pile("Herb Gatherer")
    state.supply["Acolyte"] = 1
    player.cost_reduction = 2
    get_card(source).play_effect(state)
    assert menus == [{"Acolyte", "Nobles"}]
    assert [c.name for c in player.discard] == ["Acolyte"]
    assert state.supply["Acolyte"] == 0
    assert state.top_supply_card("Herb Gatherer") == "Sorceress"
    assert state.supply["Herb Gatherer"] == 10


def test_engineer_context_tracks_actual_first_gain_and_self_trash():
    class Strategy(EnhancedStrategy):
        def choose_free_gain(self, state, player, choices, context):
            assert context.source == "Engineer" and context.destination == "discard"
            assert context.source_card is engineer
            assert context.hand == tuple(player.hand)
            if context.gain_number == 1:
                assert context.can_trash_source and context.previous_gain is None
                assert context.owned_counts["Engineer"] == 1
                return get_card("Village")
            assert context.gain_number == 2 and not context.can_trash_source
            assert context.sacrificed is engineer and engineer in state.trash
            assert context.previous_gain.name == "Silver"  # Trader replaced Village.
            assert context.owned_counts["Silver"] == 1
            assert "Engineer" not in context.owned_counts
            return get_card("Smithy")

        def should_trash_engineer_for_extra_gains(self, state, player, source):
            assert player.discard[-1].name == "Silver"
            return True

    state, player = make_state(Strategy(), ("Village", "Smithy", "Silver"))
    engineer = get_card("Engineer")
    player.in_play = [engineer]
    player.hand = [get_card("Trader")]
    player.ai.should_reveal_trader = lambda s, p, c, **kwargs: c.name == "Village"
    engineer.play_effect(state)
    assert [c.name for c in player.discard] == ["Silver", "Smithy"]
    assert engineer in state.trash and engineer not in player.in_play


def test_engineer_rebuilds_second_menu_after_first_gain_and_trash_hooks():
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Villa"), PriorityRule("Gold"), PriorityRule("Village")]
    strategy.should_trash_engineer_for_extra_gains = lambda *args: True
    state, player = make_state(strategy, ("Villa", "Village", "Gold"))
    state.supply["Villa"] = 1
    state.supply["Gold"] = 1
    player.cost_reduction = 2
    engineer = get_card("Engineer")
    player.in_play = [engineer]
    player.hand = [get_card("Market Square")]
    player.ai.should_react_with_market_square = lambda *args: True
    # The first gain consumes Villa; the trash reaction consumes Gold.
    engineer.play_effect(state)
    assert state.supply["Gold"] == 0 and state.supply["Villa"] == 0
    assert [c.name for c in player.hand] == ["Villa"]
    assert player.count("Gold") == 1 and player.count("Village") == 1
    assert engineer in state.trash


@pytest.mark.parametrize("source", ["Ironworks", "Engineer"])
def test_legacy_decline_preserves_old_fallback_and_new_policy_can_opt_in(source):
    strategy = EnhancedStrategy()
    state, player = make_state(strategy, ("Ironworks", "Silver"))
    player.deck += [get_card("Ironworks") for _ in range(6)]
    get_card(source).play_effect(state)
    assert player.discard[-1].name == "Ironworks"
    strategy.free_gain_priority = []
    get_card(source).play_effect(state)
    assert player.discard[-1].name == "Silver"


@pytest.mark.parametrize("in_play", [False, True])
def test_engineer_default_keep_and_explicit_empty_menu_self_trash(in_play):
    strategy = EnhancedStrategy()
    state, player = make_state(strategy, ("Province",))
    engineer = get_card("Engineer")
    player.in_play = [engineer] if in_play else []
    engineer.play_effect(state)
    assert state.trash == []
    strategy.should_trash_engineer_for_extra_gains = lambda *args: True
    engineer.play_effect(state)
    assert (engineer in state.trash) is in_play
    assert player.discard == []


def test_replayed_trashed_engineer_gets_only_its_first_gain():
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Silver")]
    strategy.should_trash_engineer_for_extra_gains = lambda *args: True
    state, player = make_state(strategy, ("Silver",))
    engineer = get_card("Engineer")
    player.in_play = [engineer]
    engineer.play_effect(state)
    engineer.play_effect(state)
    assert player.count("Silver") == 3
    assert state.trash == [engineer]


@pytest.mark.parametrize("modifier,target,actions,coins,cards", [
    ("Capitalism", "Bridge", 1, 1, 0),
    ("Enlightenment", "Silver", 1, 1, 0),
    ("Inheritance", "Estate", 1, 0, 1),
    ("Inheritance and Capitalism", "Estate", 1, 1, 1),
    ("Snowy Village", "Mill", 0, 0, 1),
    (None, "Mill", 1, 0, 1),
])
def test_ironworks_bonuses_use_all_live_types(modifier, target, actions, coins, cards):
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule(target)]
    state, player = make_state(strategy, (target,))
    state.phase = "action"
    if modifier == "Capitalism":
        player.projects = [Capitalism()]
    elif modifier == "Enlightenment":
        state.prophecy = get_prophecy("Enlightenment")
        state.prophecy.is_active = True
    elif modifier == "Inheritance":
        player.inherited_action_name = "Village"
    elif modifier == "Inheritance and Capitalism":
        player.inherited_action_name = "Bridge"
        player.projects = [Capitalism()]
    elif modifier == "Snowy Village":
        player.ignore_action_bonuses = True
    player.actions = 0
    get_card("Ironworks").play_effect(state)
    assert (player.actions, player.coins, len(player.hand)) == (actions, coins, cards)


@pytest.mark.parametrize("reaction", ["topdeck", "trash", "trader", "changeling"])
def test_ironworks_pays_for_actual_gain_after_replacement_before_exchange(reaction):
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Mill")]
    state, player = make_state(strategy, ("Mill", "Silver", "Changeling"))
    player.actions = 0
    if reaction in {"topdeck", "trash"}:
        player.hand = [get_card("Watchtower")]
        strategy.choose_watchtower_reaction = lambda *args: reaction
    elif reaction == "trader":
        player.hand = [get_card("Trader")]
        player.ai.should_reveal_trader = lambda *args, **kwargs: True
    else:
        player.ai.should_exchange_changeling = lambda *args: True
    get_card("Ironworks").play_effect(state)
    assert player.coins == (reaction == "trader")
    assert player.actions == (reaction != "trader")
    if reaction == "changeling":
        assert [c.name for c in player.discard] == ["Changeling"]
        assert len(player.hand) == 1
        assert state.supply["Mill"] == 10
    elif reaction == "trash":
        assert state.trash[0].name == "Mill"
        assert len(player.hand) == 2
    elif reaction == "topdeck":
        assert player.hand[-1].name == "Mill"  # +1 Card draws the topdecked gain.


def test_contextual_ironworks_values_live_immediate_bonuses_and_stranded_actions():
    state, player = make_state(names=("Silver",))
    player.actions = 0
    player.hand = [get_card("Smithy")]
    context = FreeGainContext.build(state, player, "Ironworks")
    silver = get_card("Silver")
    ordinary = tactical_defaults.free_gain_value(state, player, silver, context)
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    assert tactical_defaults.free_gain_value(state, player, silver, context) == ordinary + 3


@pytest.mark.parametrize("source", ["Ironworks", "Engineer"])
@pytest.mark.parametrize("reaction", [None, "trash", "changeling", "trader"])
def test_teacher_records_final_gain_with_pre_gain_observation(source, reaction):
    state, player, teacher = teacher_state(("Village", "Silver", "Curse", "Changeling"))
    from dominion.rl.action_encoder import ActionEncoder
    teacher.actions = ActionEncoder(list(teacher.actions.card_to_idx) + ["Changeling"])
    if reaction == "trash":
        player.hand = [get_card("Watchtower")]
        teacher.strategy.choose_watchtower_reaction = lambda *args: "trash"
    elif reaction == "changeling":
        teacher.should_exchange_changeling = lambda *args: True
    elif reaction == "trader":
        player.hand = [get_card("Trader")]
        teacher.should_reveal_trader = lambda *args, **kwargs: True
    get_card(source).play_effect(state)
    assert labels(teacher) == ([] if reaction == "trader" else [("buy", "Village")])
    if teacher.examples:
        observation, mask, target, decision = teacher.examples[0]
        assert observation["supply"]["Village"] == 10 and observation["discard"] == ()
        assert mask[target] and decision == "buy"


@pytest.mark.parametrize("source", ["Ironworks", "Engineer"])
def test_empty_gain_menu_does_not_request_a_policy_choice(source):
    strategy = EnhancedStrategy()
    strategy.choose_free_gain = lambda *args: pytest.fail("No legal gain to choose")
    state, player = make_state(strategy, ("Engineer", "Alchemist"))
    get_card(source).play_effect(state)
    assert player.discard == []


def test_engineer_teacher_records_both_gains_after_self_trash():
    state, player, teacher = teacher_state(("Village", "Silver", "Curse"))
    state.supply["Village"] = 1
    teacher.strategy.free_gain_priority = [PriorityRule("Village"), PriorityRule("Silver")]
    teacher.strategy.should_trash_engineer_for_extra_gains = lambda *args: True
    engineer = get_card("Engineer")
    player.in_play = [engineer]
    engineer.play_effect(state)
    assert labels(teacher) == [("buy", "Village"), ("buy", "Silver")]
    second, _, _, _ = teacher.examples[1]
    assert second["supply"]["Village"] == 0 and second["trash"] == ("Engineer",)
    assert second["discard"] == ("Village",)
