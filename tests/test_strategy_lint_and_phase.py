from types import SimpleNamespace

from dominion.boards.loader import BoardConfig
from dominion.cards.registry import get_card
from dominion.events.looting import Looting
from dominion.projects.sewers import Sewers
from dominion.strategy.card_roles import cards_with_role, infer_card_roles
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.lint import cleanup_for_publication, lint_strategy, normalize_strategy
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


def test_lint_flags_cantrip_after_ungated_terminal():
    strategy = EnhancedStrategy()
    strategy.action_priority = [
        PriorityRule("Watchtower"),
        PriorityRule("Peddler"),
    ]

    warnings = lint_strategy(strategy)

    assert "CANTRIP_AFTER_TERMINAL" in {warning.code for warning in warnings}


def test_cleanup_for_publication_drops_actions_not_in_gain_plan_on_simple_board():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("City"),
        PriorityRule("Peddler"),
        PriorityRule("Silver"),
    ]
    strategy.action_priority = [
        PriorityRule("City"),
        PriorityRule("Watchtower"),
        PriorityRule("Peddler"),
    ]

    cleaned = cleanup_for_publication(
        strategy,
        board_config=BoardConfig(["City", "Watchtower", "Peddler"]),
    )

    assert [rule.card_name for rule in cleaned.action_priority] == [
        "City",
        "Peddler",
    ]
    assert [rule.card_name for rule in strategy.action_priority] == [
        "City",
        "Watchtower",
        "Peddler",
    ]


def test_cleanup_for_publication_keeps_actions_without_explicit_gain_plan():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Smithy")]

    cleaned = cleanup_for_publication(strategy)

    assert [rule.card_name for rule in cleaned.action_priority] == ["Smithy"]


def test_cleanup_for_publication_keeps_actions_without_board_context():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    strategy.action_priority = [PriorityRule("Smithy")]

    cleaned = cleanup_for_publication(strategy)

    assert [rule.card_name for rule in cleaned.action_priority] == ["Smithy"]


def test_cleanup_for_publication_keeps_off_menu_actions_with_collection():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("Collection"),
        PriorityRule("Silver"),
    ]
    strategy.action_priority = [
        PriorityRule("Smithy"),
        PriorityRule("Village"),
    ]

    cleaned = cleanup_for_publication(strategy)

    assert [rule.card_name for rule in cleaned.action_priority] == [
        "Smithy",
        "Village",
    ]


def test_cleanup_for_publication_keeps_actions_on_event_boards():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    strategy.action_priority = [PriorityRule("Smithy")]

    cleaned = cleanup_for_publication(
        strategy,
        board_config=BoardConfig(["Smithy"], events=["Seaway"]),
    )

    assert [rule.card_name for rule in cleaned.action_priority] == ["Smithy"]


def test_cleanup_for_publication_keeps_actions_on_ally_boards():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    strategy.action_priority = [PriorityRule("Smithy")]

    cleaned = cleanup_for_publication(
        strategy,
        board_config=BoardConfig(["Smithy"], allies=["Crafters' Guild"]),
    )

    assert [rule.card_name for rule in cleaned.action_priority] == ["Smithy"]


def test_cleanup_for_publication_keeps_actions_on_trait_boards():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    strategy.action_priority = [PriorityRule("Smithy")]

    cleaned = cleanup_for_publication(
        strategy,
        board_config=BoardConfig(["Smithy"], traits={"Smithy": "Inherited"}),
    )

    assert [rule.card_name for rule in cleaned.action_priority] == ["Smithy"]


def test_cleanup_for_publication_keeps_actions_on_omen_boards():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    strategy.action_priority = [PriorityRule("Smithy")]

    cleaned = cleanup_for_publication(
        strategy,
        board_config=BoardConfig(["Rustic Village", "Smithy"]),
    )

    assert [rule.card_name for rule in cleaned.action_priority] == ["Smithy"]


def test_cleanup_for_publication_keeps_actions_with_quartermaster():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("Quartermaster"),
        PriorityRule("Silver"),
    ]
    strategy.action_priority = [
        PriorityRule("Smithy"),
        PriorityRule("Village"),
    ]

    cleaned = cleanup_for_publication(
        strategy,
        board_config=BoardConfig(["Quartermaster", "Smithy", "Village"]),
    )

    assert [rule.card_name for rule in cleaned.action_priority] == [
        "Smithy",
        "Village",
    ]


def test_cleanup_for_publication_keeps_actions_with_forge():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("Forge"),
        PriorityRule("Silver"),
    ]
    strategy.action_priority = [
        PriorityRule("Smithy"),
        PriorityRule("Village"),
    ]

    cleaned = cleanup_for_publication(
        strategy,
        board_config=BoardConfig(["Forge", "Smithy", "Village"]),
    )

    assert [rule.card_name for rule in cleaned.action_priority] == [
        "Smithy",
        "Village",
    ]


def test_cleanup_for_publication_keeps_trail_action_rule():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("Silver"),
    ]
    strategy.action_priority = [
        PriorityRule("Trail"),
        PriorityRule("Smithy"),
    ]

    cleaned = cleanup_for_publication(strategy, board_config=BoardConfig(["Trail", "Smithy"]))

    assert [rule.card_name for rule in cleaned.action_priority] == ["Trail"]


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
