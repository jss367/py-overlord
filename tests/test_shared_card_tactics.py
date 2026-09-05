"""Exercise tactical defaults through card effects and the strategy adapter."""

from types import SimpleNamespace

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
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
    player.duration = [get_card("Quartermaster")]
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in state.quartermaster_mats[id(player)]] == ["Village"]
    assert state.supply["Village"] == 9
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in player.hand] == ["Village"]
    assert state.quartermaster_mats[id(player)] == []


def test_quartermaster_specific_gain_override_can_differ_from_buy_preferences():
    class Strategy(EnhancedStrategy):
        def choose_quartermaster_gain(self, state, player, choices):
            return next(c for c in choices if c.name == "Smithy")

    strategy = Strategy()
    strategy.gain_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    player.duration = [get_card("Quartermaster")]
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in state.quartermaster_mats[id(player)]] == ["Smithy"]


@pytest.mark.parametrize("invalid", [None, "Gold"])
def test_invalid_or_absent_quartermaster_selection_uses_legal_fallback(invalid):
    class Strategy(EnhancedStrategy):
        def choose_quartermaster_gain(self, state, player, choices):
            return get_card(invalid) if invalid else None

    state, player = make_state(Strategy())
    player.duration = [get_card("Quartermaster")]
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in state.quartermaster_mats[id(player)]] == ["Smithy"]


def test_quartermaster_fallback_avoids_curse_when_only_victory_is_alternative():
    state, player = make_state(names=("Curse", "Estate"))
    player.duration = [get_card("Quartermaster")]
    state._handle_quartermaster_start_of_turn(player)
    assert [c.name for c in state.quartermaster_mats[id(player)]] == ["Estate"]


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
        assert state.quartermaster_mats[id(player)][0].name == expected
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
    player.duration = [get_card("Quartermaster")]
    state._handle_quartermaster_start_of_turn(player)
    assert state.quartermaster_mats[id(player)][0].name == "Laboratory"

    state, player = make_state(names=("Hunting Grounds",))
    player.cost_reduction = 1
    get_card("Overlord").play_effect(state)
    assert len(player.hand) == 4
