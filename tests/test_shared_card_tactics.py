"""Exercise tactical defaults through card effects and the strategy adapter."""

from types import SimpleNamespace

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.ai import tactical_defaults
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.phase_strategy import PhaseAwareStrategy, StrategyPhase


def make_state(strategy=None, names=("Village", "Smithy")):
    player = PlayerState(GeneticAI(strategy or EnhancedStrategy()))
    player.deck = [get_card("Copper") for _ in range(10)]
    state = GameState([player], supply=dict.fromkeys(names, 10))
    state.log_callback = lambda *args: None
    return state, player


@pytest.mark.parametrize("names", [("Village", "Smithy"), ("Smithy", "Village")])
def test_overlord_fallback_is_independent_of_supply_order(names):
    state, player = make_state(names=names)
    get_card("Overlord").play_effect(state)
    assert len(player.hand) == 3  # Smithy when there are no Actions to support.
    assert state.supply == dict.fromkeys(names, 10)


def test_overlord_fallback_supports_terminal_actions_in_hand():
    state, player = make_state()
    player.actions = 0
    player.hand = [get_card("Smithy")]
    get_card("Overlord").play_effect(state)
    assert player.actions == 2
    assert len(player.hand) == 2


def test_overlord_uses_action_priorities_without_requiring_target_in_hand():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    get_card("Overlord").play_effect(state)
    assert player.actions == 3
    assert len(player.hand) == 1


def test_overlord_specific_override_can_differ_from_action_order():
    class Strategy(EnhancedStrategy):
        def choose_overlord_target(self, state, player, choices):
            return next(c for c in choices if c.name == "Smithy")

    strategy = Strategy()
    strategy.action_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    get_card("Overlord").play_effect(state)
    assert len(player.hand) == 3


def test_overlord_menu_excludes_commands_debt_potions_and_empty_piles():
    class Strategy(EnhancedStrategy):
        def choose_overlord_target(self, state, player, choices):
            assert {c.name for c in choices} == {"Smithy"}
            return choices[0]

    state, player = make_state(Strategy(), (
        "Overlord", "Band of Misfits", "City Quarter", "Alchemist", "Smithy", "Village",
    ))
    state.supply["Village"] = 0
    get_card("Overlord").play_effect(state)
    assert len(player.hand) == 3


@pytest.mark.parametrize("invalid", [None, "Gold"])
def test_invalid_or_absent_overlord_selection_uses_legal_fallback(invalid):
    class Strategy(EnhancedStrategy):
        def choose_overlord_target(self, state, player, choices):
            return get_card(invalid) if invalid else None

    state, player = make_state(Strategy())
    get_card("Overlord").play_effect(state)
    assert len(player.hand) == 3
    assert player.coins == 0


def test_overlord_supports_legacy_ai_without_specific_hook():
    state, player = make_state()
    player.ai = SimpleNamespace(name="legacy", choose_action=lambda *args: None)
    get_card("Overlord").play_effect(state)
    assert len(player.hand) == 3


def test_base_ai_preserves_generic_selection_for_strategies_without_new_hook():
    strategy = SimpleNamespace(
        choose_action=lambda state, player, choices: next(c for c in choices if c and c.name == "Village")
    )
    state, player = make_state(strategy)
    get_card("Overlord").play_effect(state)
    assert len(player.hand) == 1
    assert player.actions == 3


def test_quartermaster_uses_gain_priorities_and_collects_with_strategy_override():
    class Strategy(EnhancedStrategy):
        def quartermaster_take_all(self, state, player, mat):
            return bool(mat)

    strategy = Strategy()
    strategy.gain_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    qm = get_card("Quartermaster")
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in qm.set_aside] == ["Village"]
    assert state.supply["Village"] == 9
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in player.hand] == ["Village"]
    assert qm.set_aside == []


def test_quartermaster_specific_gain_override_can_differ_from_buy_preferences():
    class Strategy(EnhancedStrategy):
        def choose_quartermaster_gain(self, state, player, choices):
            return next(c for c in choices if c.name == "Smithy")

    strategy = Strategy()
    strategy.gain_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    qm = get_card("Quartermaster")
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in qm.set_aside] == ["Smithy"]


@pytest.mark.parametrize("invalid", [None, "Gold"])
def test_invalid_or_absent_quartermaster_selection_uses_legal_fallback(invalid):
    class Strategy(EnhancedStrategy):
        def choose_quartermaster_gain(self, state, player, choices):
            return get_card(invalid) if invalid else None

    state, player = make_state(Strategy())
    qm = get_card("Quartermaster")
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in qm.set_aside] == ["Smithy"]


def test_quartermaster_fallback_avoids_curse_when_only_victory_is_alternative():
    state, player = make_state(names=("Curse", "Estate"))
    qm = get_card("Quartermaster")
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in qm.set_aside] == ["Estate"]


def test_card_specific_choices_respect_phase_preferences():
    strategy = PhaseAwareStrategy()
    strategy.phase_action_priority[StrategyPhase.ENDGAME] = [PriorityRule("Village")]
    strategy.phase_gain_priority[StrategyPhase.ENDGAME] = [PriorityRule("Village")]
    state, player = make_state(strategy)
    choices = [get_card("Smithy"), get_card("Village")]
    assert player.ai.choose_overlord_target(state, player, choices).name == "Village"
    assert player.ai.choose_quartermaster_gain(state, player, choices).name == "Village"


def test_failed_priority_conditions_prefer_unspecified_alternatives():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Smithy", lambda *_: False)]
    strategy.gain_priority = [PriorityRule("Smithy", lambda *_: False)]
    state, player = make_state(strategy)
    choices = [get_card("Smithy"), get_card("Village")]
    assert player.ai.choose_overlord_target(state, player, choices).name == "Village"
    assert player.ai.choose_quartermaster_gain(state, player, choices).name == "Village"


@pytest.mark.parametrize("phase, expected", [
    (StrategyPhase.ENDGAME, "Village"),
    (StrategyPhase.OPENING, "Smithy"),
])
@pytest.mark.parametrize("card_name", ["Overlord", "Quartermaster"])
def test_tactical_fallback_deprioritizes_only_active_phase_rules(phase, expected, card_name):
    strategy = PhaseAwareStrategy()
    strategy.phase_action_priority[phase] = [PriorityRule("Smithy", lambda *_: False)]
    strategy.phase_gain_priority[phase] = [PriorityRule("Smithy", lambda *_: False)]
    state, player = make_state(strategy)
    assert strategy.classify_phase(state, player) == StrategyPhase.ENDGAME

    get_card(card_name).play_effect(state)
    if card_name == "Quartermaster":
        state._handle_quartermaster_start_of_turn(player)
        assert player.duration[0].set_aside[0].name == expected
    else:
        assert len(player.hand) == (1 if expected == "Village" else 3)


@pytest.mark.parametrize("card_name, target", [("Overlord", "Gold"), ("Quartermaster", "Province")])
def test_no_eligible_targets_are_a_noop(card_name, target):
    state, player = make_state(names=(target,))
    card = get_card(card_name)
    card.play_effect(state)
    if card_name == "Quartermaster":
        state._handle_quartermaster_start_of_turn(player)
    assert state.supply[target] == 10
    assert player.hand == []


def test_modified_costs_are_used_in_both_menus():
    state, player = make_state(names=("Laboratory",))
    player.cost_reduction = 1
    qm = get_card("Quartermaster")
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert qm.set_aside[0].name == "Laboratory"

    state, player = make_state(names=("Hunting Grounds",))
    player.cost_reduction = 1
    get_card("Overlord").play_effect(state)
    assert len(player.hand) == 4


SUPPLY_COMMANDS = [
    ("Captain", "choose_captain_target", "captain_target_priority"),
    ("Band of Misfits", "choose_band_of_misfits_target", "band_of_misfits_target_priority"),
]


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
def test_supply_preferences_are_independent_of_hand_play_order(card_name, hook, priority):
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Village")]
    setattr(strategy, priority, [PriorityRule("Smithy")])
    state, player = make_state(strategy)
    get_card(card_name).play_effect(state)
    assert len(player.hand) == 3
    assert strategy.choose_action(state, player, [get_card("Village"), get_card("Smithy")]).name == "Village"


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
def test_supply_specific_override_is_forwarded(card_name, hook, priority):
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Village")]
    calls = []

    def select(state, player, choices):
        calls.append({c.name for c in choices})
        return next(c for c in choices if c.name == "Smithy")

    setattr(strategy, hook, select)
    state, player = make_state(strategy)
    get_card(card_name).play_effect(state)
    assert calls == [{"Village", "Smithy"}]
    assert len(player.hand) == 3


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
@pytest.mark.parametrize("condition, expected", [(True, 3), (False, 1)])
def test_supply_conditional_preferences(card_name, hook, priority, condition, expected):
    strategy = EnhancedStrategy()
    setattr(strategy, priority, [PriorityRule("Smithy", lambda *_: condition)])
    # A hand rule must not reinstate a target rejected by a supply rule.
    strategy.action_priority = [PriorityRule("Smithy")]
    state, player = make_state(strategy)
    get_card(card_name).play_effect(state)
    assert len(player.hand) == expected


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
def test_all_supply_conditions_failing_still_plays_mandatory_target(card_name, hook, priority):
    strategy = EnhancedStrategy()
    setattr(strategy, priority, [PriorityRule("Smithy", lambda *_: False)])
    state, player = make_state(strategy, names=("Smithy",))
    get_card(card_name).play_effect(state)
    assert len(player.hand) == 3


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
@pytest.mark.parametrize("invalid", [None, "Gold", "Wharf", "Overlord", "bad type"])
@pytest.mark.parametrize("names", [("Village", "Smithy"), ("Smithy", "Village")])
def test_supply_invalid_selection_is_mandatory_and_deterministic(card_name, hook, priority, invalid, names):
    strategy = EnhancedStrategy()
    selection = invalid if invalid == "bad type" else get_card(invalid) if invalid else None
    setattr(strategy, hook, lambda *_: selection)
    state, player = make_state(strategy, names=names)
    get_card(card_name).play_effect(state)
    assert len(player.hand) == 3
    assert state.supply == dict.fromkeys(names, 10)


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
def test_empty_supply_menu_does_not_call_strategy(card_name, hook, priority):
    strategy = EnhancedStrategy()
    setattr(strategy, hook, lambda *_: pytest.fail("Empty menu reached strategy"))
    state, player = make_state(strategy, names=("Gold", "Village", "Overlord"))
    state.supply["Village"] = 0
    get_card(card_name).play_effect(state)
    assert player.hand == []


@pytest.mark.parametrize("card_name, expected", [
    ("Captain", {"Smithy"}),
    ("Band of Misfits", {"Smithy", "Caravan"}),
    ("Overlord", {"Smithy", "Caravan", "Laboratory"}),
])
def test_supply_command_menus(card_name, expected):
    strategy = EnhancedStrategy()
    hook = "choose_" + card_name.lower().replace(" ", "_") + "_target"

    def select(state, player, choices):
        assert {c.name for c in choices} == expected
        return get_card("Smithy")

    setattr(strategy, hook, select)
    state, player = make_state(strategy, names=(
        "Captain", "Band of Misfits", "Overlord", "City Quarter", "Alchemist",
        "Smithy", "Caravan", "Laboratory", "Village", "Horse",
    ))
    state.supply["Village"] = 0
    state.non_supply_pile_names.add("Horse")
    get_card(card_name).play_effect(state)
    assert len(player.hand) == 3


def test_captain_uses_current_cost_on_both_plays():
    state, player = make_state(names=("Laboratory",))
    captain = get_card("Captain")
    captain.play_effect(state)
    assert not player.hand
    assert captain in player.duration  # Even with no legal first-turn target.
    player.cost_reduction = 1
    captain.on_duration(state)
    assert len(player.hand) == 2
    assert state.supply["Laboratory"] == 10


def test_band_of_misfits_compares_both_modified_costs_and_cost_floor():
    strategy = EnhancedStrategy()
    menus = []
    strategy.choose_band_of_misfits_target = lambda _s, _p, cs: menus.append({c.name for c in cs}) or None
    state, player = make_state(strategy, names=("Smithy", "Laboratory", "Village"))
    player.cost_reduction = 2
    get_card("Band of Misfits").play_effect(state)
    assert menus == [{"Smithy", "Village"}]  # Lab is still equal to Misfits.
    player.cost_reduction = 5
    get_card("Band of Misfits").play_effect(state)
    assert len(menus) == 1  # Nothing costs less than $0.


@pytest.mark.parametrize("card_name", ["Captain", "Band of Misfits", "Overlord"])
def test_supply_menu_respects_pile_specific_discount_and_not_buy_restrictions(card_name):
    state, player = make_state(names=("Grand Market",))
    player.in_play = [get_card("Copper")]
    state.family_inventor_tokens = {"Grand Market": 2}
    assert not get_card("Grand Market").may_be_bought(state)
    get_card(card_name).play_effect(state)
    assert len(player.hand) == 1
    assert player.coins == 2


def test_supply_menu_only_offers_exposed_split_and_knight_cards():
    state, player = make_state(names=("Encampment", "Plunder", "Knights"))
    state.pile_order["Knights"] = ["Dame Anna", "Sir Martin"]
    from dominion.cards.supply_play import supply_action_choices

    choices = supply_action_choices(state, player, 4)
    assert {c.name for c in choices} == {"Encampment", "Sir Martin"}
    state.supply["Encampment"] = 0
    assert {c.name for c in supply_action_choices(state, player, 4)} == {"Sir Martin"}


def test_supply_menu_includes_live_action_types_and_top_ruins():
    from dominion.cards.supply_play import supply_action_choices
    from dominion.prophecies.registry import get_prophecy

    state, player = make_state(names=("Silver", "Ruins"))
    state.pile_order["Ruins"] = ["Ruined Village", "Abandoned Mine"]
    assert {c.name for c in supply_action_choices(state, player, 4)} == {"Abandoned Mine"}
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    assert {c.name for c in supply_action_choices(state, player, 4)} == {"Silver", "Abandoned Mine"}


@pytest.mark.parametrize("card_name", ["Captain", "Band of Misfits", "Overlord"])
def test_enlightenment_supply_treasure_uses_action_substitution(card_name):
    from dominion.prophecies.registry import get_prophecy

    state, player = make_state(names=("Silver",))
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    state.phase = "action"
    get_card(card_name).play_effect(state)
    assert len(player.hand) == 1
    assert player.actions == 2
    assert player.coins == 0
    assert player.actions_played == 1
    assert player.actions_this_turn == 1
    assert state.supply["Silver"] == 10
    assert all(c.name != "Silver" for c in player.all_cards())


@pytest.mark.parametrize("card_name", ["Captain", "Band of Misfits", "Overlord"])
def test_enlightenment_supply_treasure_offers_a_way_without_moving_it(card_name):
    from dominion.prophecies.registry import get_prophecy
    from dominion.ways.registry import get_way

    strategy = EnhancedStrategy()
    offered = []
    turtle = get_way("Way of the Turtle")

    def choose_way(state, player, card, ways):
        offered.append(card.name)
        return turtle

    strategy.choose_way = choose_way
    state, player = make_state(strategy, names=("Silver",))
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    state.phase = "action"
    state.ways = [turtle]
    get_card(card_name).play_effect(state)
    assert offered == ["Silver"]
    assert not getattr(player, "turtle_set_aside", [])
    assert player.hand == []
    assert player.coins == 0
    assert player.actions_played == 1
    assert state.supply["Silver"] == 10


def test_supply_menu_excludes_ferryman_set_aside_pile():
    from dominion.cards.supply_play import supply_action_choices

    state, player = make_state(names=("Smithy", "Village"))
    state.ferryman_card_name = "Smithy"
    assert {c.name for c in supply_action_choices(state, player, 4)} == {"Village"}


def test_captain_reselects_with_next_turn_context_through_strategy():
    strategy = EnhancedStrategy()
    strategy.captain_target_priority = [PriorityRule("Village", lambda _s, p: p.actions == 0)]
    state, player = make_state(strategy)
    captain = get_card("Captain")
    captain.play_effect(state)
    assert len(player.hand) == 3
    assert player.actions_played == 1
    player.actions = 0
    captain.on_duration(state)
    assert len(player.hand) == 4
    assert player.actions == 2
    assert player.actions_played == 2
    assert state.supply == {"Village": 10, "Smithy": 10}


@pytest.mark.parametrize("hook", ["choose_captain_target", "choose_band_of_misfits_target"])
def test_adapter_without_strategy_hook_uses_shared_baseline(hook):
    state, player = make_state()
    player.ai.strategy = SimpleNamespace(choose_action=lambda *_: pytest.fail("Hand selector called"))
    assert getattr(player.ai, hook)(state, player, [get_card("Village"), get_card("Smithy")]).name == "Smithy"


@pytest.mark.parametrize("junk_count, expected", [(0, "Smithy"), (1, "Smithy"), (3, "Chapel")])
def test_supply_baseline_values_trashing_according_to_hand(junk_count, expected):
    state, player = make_state()
    player.hand = [get_card("Estate") for _ in range(junk_count)]
    assert tactical_defaults.choose_supply_action_target(
        state, player, [get_card("Chapel"), get_card("Smithy")]
    ).name == expected


def test_supply_baseline_keeps_endgame_victory_cards():
    state, player = make_state()
    state.supply["Province"] = 2
    player.hand = [get_card("Estate") for _ in range(3)]
    assert tactical_defaults.choose_supply_action_target(
        state, player, [get_card("Chapel"), get_card("Smithy")]
    ).name == "Smithy"


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
def test_supply_baseline_supports_excess_command_copies(card_name, hook, priority):
    state, player = make_state()
    player.actions = 0
    player.hand = [get_card(card_name) for _ in range(3)]
    get_card(card_name).play_effect(state)
    assert player.actions == 2  # Village unlocks the other Commands.
    assert len(player.hand) == 4


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
def test_phase_hand_rules_do_not_affect_dedicated_supply_priorities(card_name, hook, priority):
    strategy = PhaseAwareStrategy()
    strategy.phase_action_priority[StrategyPhase.ENDGAME] = [PriorityRule("Smithy", lambda *_: False)]
    state, player = make_state(strategy)
    get_card(card_name).play_effect(state)
    assert len(player.hand) == 3


@pytest.mark.parametrize("card_name, priority, target", [
    ("Captain", "captain_target_priority", "Smithy"),
    ("Band of Misfits", "band_of_misfits_target_priority", "Militia"),
])
def test_supply_only_reference_is_available_on_an_inferred_board(card_name, priority, target):
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule(card_name)]
    setattr(strategy, priority, [PriorityRule(target, lambda _s, p: p.actions > 0)])
    with StrategyBattle(log_frequency=0) as battle:
        names = battle._determine_kingdom_cards(strategy, EnhancedStrategy())
    assert set(names) == {card_name, target}
    state, player = make_state(strategy, names=names)
    get_card(card_name).play_effect(state)
    if target == "Smithy":
        assert len(player.hand) == 3
    else:
        assert player.coins == 2


@pytest.mark.parametrize("priority, target", [
    ("free_gain_priority", "Smithy"),
    ("captain_target_priority", "Smithy"),
    ("band_of_misfits_target_priority", "Militia"),
])
def test_supply_only_references_appear_in_catalog_metadata(monkeypatch, priority, target):
    from dominion.reporting.strategy_pages import collect_rendered_strategies
    from dominion.strategy.strategy_loader import StrategyLoader

    strategy = EnhancedStrategy()
    setattr(strategy, priority, [PriorityRule(target)])
    monkeypatch.setattr(StrategyLoader, "get_strategy", lambda self, name: strategy)
    rendered = collect_rendered_strategies(names=["Big Money"])[0]
    assert rendered.references["Kingdom Cards"] == [target]


@pytest.mark.parametrize("hand_size, expected", [(3, "Smithy"), (5, "Smithy"), (6, "Militia")])
def test_supply_baseline_values_attack_pressure(hand_size, expected):
    state, player = make_state()
    opponent = PlayerState(GeneticAI(EnhancedStrategy()))
    opponent.hand = [get_card("Copper") for _ in range(hand_size)]
    state.players.append(opponent)
    assert tactical_defaults.choose_supply_action_target(
        state, player, [get_card("Militia"), get_card("Smithy")]
    ).name == expected


@pytest.mark.parametrize("curses, expected", [(0, "Smithy"), (10, "Witch")])
def test_supply_baseline_does_not_value_exhausted_cursing(curses, expected):
    state, player = make_state()
    state.players.append(PlayerState(GeneticAI(EnhancedStrategy())))
    state.supply["Curse"] = curses
    assert tactical_defaults.choose_supply_action_target(
        state, player, [get_card("Witch"), get_card("Smithy")]
    ).name == expected


@pytest.mark.parametrize("provinces, expected", [(8, "Wharf"), (2, "Smithy")])
def test_supply_baseline_values_duration_horizon(provinces, expected):
    state, player = make_state()
    state.supply["Province"] = provinces
    assert tactical_defaults.choose_supply_action_target(
        state, player, [get_card("Wharf"), get_card("Smithy")]
    ).name == expected


def test_supply_baseline_caps_draw_and_avoids_mandatory_good_card_trash():
    state, player = make_state()
    player.deck = []
    player.hand = [get_card("Gold")]
    assert tactical_defaults.choose_supply_action_target(
        state, player, [get_card("Junk Dealer"), get_card("Smithy"), get_card("Militia")]
    ).name == "Militia"
    assert tactical_defaults.choose_supply_action_target(state, player, []) is None


@pytest.mark.parametrize("card_name", ["Captain", "Band of Misfits"])
def test_virtual_feast_gains_without_trashing_itself(card_name):
    state, player = make_state(names=("Feast", "Laboratory"))
    get_card(card_name).play_effect(state)
    assert [c.name for c in player.discard] == ["Laboratory"]
    assert state.supply == {"Feast": 10, "Laboratory": 9}
    assert state.trash == []


def test_supply_baseline_does_not_penalize_unconditional_self_trash_effects():
    state, player = make_state()
    assert tactical_defaults.choose_supply_action_target(
        state, player, [get_card("Feast"), get_card("Pillage")]
    ).name == "Feast"


@pytest.mark.parametrize("card_name, hook, priority", SUPPLY_COMMANDS)
def test_supply_play_indirectly_uses_the_same_dedicated_target(card_name, hook, priority):
    strategy = EnhancedStrategy()
    setattr(strategy, priority, [PriorityRule("Smithy")])
    state, player = make_state(strategy)
    command = get_card(card_name)
    player.in_play = [command]
    state.play_action_indirectly(player, command)
    assert len(player.hand) == 3
    assert state.supply == {"Village": 10, "Smithy": 10}
    assert all(c.name != "Smithy" for c in player.in_play)


def test_audited_captain_duration_finishes_after_next_turn():
    state, player = make_state(names=("Village",))
    captain = get_card("Captain")
    player.in_play = [captain]
    captain.play_effect(state)
    state.do_duration_phase()
    assert captain not in player.duration


@pytest.mark.parametrize("card_name", ["Overlord", "Band of Misfits"])
def test_audited_command_supply_play_counts_as_an_action(card_name):
    state, player = make_state(names=("Village",))
    command = get_card(card_name)
    player.in_play = [command]
    state.play_action_indirectly(player, command)
    assert player.actions_played == 2


@pytest.mark.parametrize("card_name", ["Overlord", "Band of Misfits"])
def test_audited_supply_duration_never_becomes_owned(card_name):
    state, player = make_state(names=("Caravan",))
    command = get_card(card_name)
    player.in_play = [command]
    command.play_effect(state)
    assert all(c.name != "Caravan" for c in player.all_cards())


def test_audited_virtual_pillage_has_no_conditional_payoff():
    state, player = make_state(names=("Pillage", "Spoils"))
    player.cost_reduction = 1
    get_card("Captain").play_effect(state)
    assert state.supply["Pillage"] == 10
    assert player.count_in_deck("Spoils") == 0


@pytest.mark.parametrize("rules,expected", [
    (None, set()), ([], set()), ([PriorityRule("Smithy")], {"Smithy"}),
])
def test_dynamic_board_discovers_free_gain_only_targets(rules, expected):
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Workshop")]
    strategy.free_gain_priority = rules
    with StrategyBattle() as battle:
        names = set(battle._determine_kingdom_cards(strategy, EnhancedStrategy()))
    assert "Workshop" in names
    assert names & {"Smithy"} == expected
    if expected:
        state, player = make_state(strategy, names=names)
        get_card("Workshop").play_effect(state)
        assert player.discard[-1].name == "Smithy"


def test_explicit_board_remains_authoritative_over_free_gain_references():
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Smithy")]
    with StrategyBattle(kingdom_cards=["Workshop"]) as battle:
        assert battle._determine_kingdom_cards(strategy, EnhancedStrategy()) == ["Workshop"]
