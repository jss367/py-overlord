from types import SimpleNamespace

from dominion.cards.registry import get_card
from dominion.events.looting import Looting
from dominion.projects.sewers import Sewers
from dominion.strategy.card_roles import cards_with_role, infer_card_roles
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.lint import lint_strategy, normalize_strategy
from dominion.strategy.phase_strategy import PhaseAwareStrategy, StrategyPhase


def _state(turn_number=5, provinces_left=8, empty_piles=0):
    return SimpleNamespace(
        turn_number=turn_number,
        supply={"Province": provinces_left},
        empty_piles=empty_piles,
    )


def _player(cards=None):
    cards = cards or []
    return SimpleNamespace(
        collection_played=0,
        all_cards=lambda: list(cards),
        count_in_deck=lambda name: sum(1 for card in cards if card.name == name),
    )


def test_lint_flags_unreachable_duplicate_and_green_noise():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("Duchy"),
        PriorityRule("Gold"),
        PriorityRule("Gold"),
        PriorityRule("Province"),
        PriorityRule("Gold", PriorityRule.turn_number("<=", 5)),
        PriorityRule("Copper"),
    ]

    warnings = lint_strategy(strategy)
    codes = {warning.code for warning in warnings}

    assert "UNCONDITIONAL_GREEN_BEFORE_PROVINCE" in codes
    assert "DUPLICATE_RULE" in codes
    assert "UNREACHABLE_AFTER_UNCONDITIONAL" in codes
    assert "UNCONDITIONAL_JUNK_GAIN" in codes


def test_normalize_strategy_drops_behavior_preserving_dead_rules():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("Gold"),
        PriorityRule("Gold"),
        PriorityRule("Gold", PriorityRule.turn_number("<=", 5)),
    ]

    normalized = normalize_strategy(strategy)

    assert [rule.card_name for rule in normalized.gain_priority] == ["Gold"]


def test_card_role_inference_identifies_village_and_terminal_draw():
    village = infer_card_roles("Village")
    smithy = infer_card_roles("Smithy")

    assert village.has("village")
    assert village.has("nonterminal")
    assert smithy.has("terminal_draw")
    assert "Village" in cards_with_role(["Village", "Smithy"], "village")


def test_card_role_inference_handles_unknown_cards():
    unknown = infer_card_roles("Definitely Not A Card")

    assert unknown.name == "Definitely Not A Card"
    assert unknown.roles == frozenset()
    assert cards_with_role(["Village", "Definitely Not A Card"], "village") == ["Village"]


def test_phase_aware_strategy_uses_phase_priority_then_fallback():
    strategy = PhaseAwareStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    strategy.phase_gain_priority[StrategyPhase.OPENING] = [PriorityRule("Chapel")]

    choice = strategy.choose_gain(
        _state(turn_number=2),
        _player(),
        [get_card("Chapel"), get_card("Silver"), None],
    )

    assert choice.name == "Chapel"

    fallback = strategy.choose_gain(
        _state(turn_number=7),
        _player(),
        [get_card("Chapel"), get_card("Silver"), None],
    )

    assert fallback.name == "Silver"


def test_collection_gain_bias_ignores_landscape_buy_choices():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    player = _player()
    player.collection_played = 1
    state = SimpleNamespace(supply={"Smithy": 10, "Silver": 40})

    choice = strategy.choose_gain(
        state,
        player,
        [Sewers(), Looting(), get_card("Silver"), get_card("Smithy"), None],
    )

    assert choice.name == "Smithy"


def test_phase_classifier_switches_to_endgame():
    strategy = PhaseAwareStrategy()

    phase = strategy.classify_phase(_state(provinces_left=2), _player())

    assert phase == StrategyPhase.ENDGAME
