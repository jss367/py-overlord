from generated_strategies.oslo_workers_village_magnate_engine import (
    OsloWorkersVillageMagnateMultiColonyEngine,
    OsloWorkersVillageMagnateRefinedEngine,
    _multi_colony_greening_gate,
)
from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.enhanced_strategy import PriorityRule
from tests.utils import ChooseFirstActionAI


def test_refined_engine_gain_conditions_have_serializable_sources():
    strategy = OsloWorkersVillageMagnateRefinedEngine()
    rules = {
        rule.card_name: rule
        for rule in strategy.gain_priority
        if rule.card_name in {"Province", "King's Court"}
    }

    for rule in rules.values():
        source = rule.condition._source
        recreated = eval(source, {"PriorityRule": PriorityRule})

        assert callable(recreated)


def _setup_colony_state():
    state = GameState(players=[])
    state.initialize_game([ChooseFirstActionAI()], [get_card("Colony")])
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    state.turn_number = 5
    return state, player


def test_multi_colony_gate_waits_for_double_colony_turn():
    state, player = _setup_colony_state()
    gate = _multi_colony_greening_gate(2, 18)
    cost = state.get_card_cost(player, get_card("Colony"))

    player.buys = 2
    player.coins = 2 * cost - 1
    assert not gate(state, player)

    player.coins = 2 * cost
    assert gate(state, player)

    player.buys = 1
    assert not gate(state, player)


def test_multi_colony_gate_commits_after_first_colony():
    state, player = _setup_colony_state()
    gate = _multi_colony_greening_gate(2, 18)

    player.buys = 1
    player.coins = 0
    player.discard = [get_card("Colony")]
    assert gate(state, player)


def test_multi_colony_gate_opens_at_fallback_turn():
    state, player = _setup_colony_state()
    gate = _multi_colony_greening_gate(2, 18)

    player.buys = 1
    player.coins = 0
    state.turn_number = 18
    assert gate(state, player)


def test_multi_colony_engine_replaces_colony_condition():
    strategy = OsloWorkersVillageMagnateMultiColonyEngine()
    colony_rule = next(
        rule for rule in strategy.gain_priority if rule.card_name == "Colony"
    )
    assert colony_rule.condition is not None


def _setup_target_preserving_action_state(hand, deck=None):
    strategy = OsloWorkersVillageMagnateMultiColonyEngine()
    state = GameState(players=[])
    state.initialize_game(
        [GeneticAI(strategy)],
        [
            get_card("Workers' Village"),
            get_card("King's Court"),
            get_card("Magnate"),
            get_card("Grand Market"),
        ],
    )
    player = state.players[0]
    player.hand = [get_card(name) for name in hand]
    player.deck = [get_card(name) for name in (deck or [])]
    player.discard = []
    player.in_play = []
    player.actions = 1
    state.phase = "action"
    return state, player


def test_target_preserving_engine_courts_the_only_other_action():
    state, player = _setup_target_preserving_action_state(
        ["King's Court", "Grand Market"]
    )

    state.handle_action_phase()

    assert [card.name for card in player.in_play] == ["King's Court", "Grand Market"]
    assert player.actions_this_turn == 4


def test_target_preserving_engine_plays_village_then_courts_magnate():
    state, player = _setup_target_preserving_action_state(
        ["Workers' Village", "King's Court", "Magnate"],
        deck=["Copper"],
    )

    state.handle_action_phase()

    assert [card.name for card in player.in_play] == [
        "Workers' Village",
        "King's Court",
        "Magnate",
    ]
    assert player.actions_this_turn == 5
