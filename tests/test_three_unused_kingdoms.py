"""Setup and decision integration for the three previously unused kingdoms."""

from collections import Counter
import json
from pathlib import Path

import pytest

from dominion.ai.base_ai import AI
from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategy_loader import StrategyLoader
from dominion.strategy.strategies.three_unused_kingdoms import (
    KINGDOMS,
    UnusedKingdomPolicy,
)
from scripts.search_three_unused_kingdoms import match


def setup(board="minion_courtier", **params):
    strategy = UnusedKingdomPolicy(board, **params)
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(
        [GeneticAI(strategy), GeneticAI(EnhancedStrategy())],
        [get_card(n) for n in KINGDOMS[board]],
    )
    return state, state.current_player


def test_all_thirty_piles_were_unused_and_are_disjoint():
    provenance = json.loads(
        Path("scripts/data/three_unused_kingdoms_provenance.json").read_text()
    )
    cards = [n for board in KINGDOMS.values() for n in board]
    assert len(cards) == len(set(cards)) == 30
    assert set(cards) <= set(provenance["unused"])
    assert {k: list(v) for k, v in KINGDOMS.items()} == provenance["boards"]


@pytest.mark.parametrize("board", KINGDOMS)
def test_board_setup_uses_ten_piles_and_standard_start(board):
    config = load_board(f"boards/{board}.txt")
    assert config.kingdom_cards == list(KINGDOMS[board])
    assert not any(
        (
            config.events,
            config.projects,
            config.ways,
            config.landmarks,
            config.allies,
            config.traits,
            config.prophecy,
            config.card_cost_reduction,
        )
    )
    state, _ = setup(board)
    assert not {"Colony", "Platinum", "Potion"} & state.supply.keys()
    for player in state.players:
        assert Counter(c.name for c in player.all_cards()) == {"Copper": 7, "Estate": 3}


def test_minion_spends_early_copies_then_redraws_and_attacks():
    state, player = setup(minion_redraw=3)
    player.hand = [get_card("Minion"), get_card("Estate"), get_card("Copper")]
    player.coins = 0
    get_card("Minion").play_effect(state)
    assert player.coins == 2
    player.hand.remove(player.hand[0])
    player.deck = [get_card("Silver") for _ in range(4)]
    target = state.players[1]
    target.hand = [get_card("Copper") for _ in range(5)]
    target.deck = [get_card("Estate") for _ in range(4)]
    get_card("Minion").play_effect(state)
    assert [c.name for c in player.hand] == ["Silver"] * 4
    assert [c.name for c in target.hand] == ["Estate"] * 4


def test_minion_keeps_guaranteed_province():
    state, player = setup()
    player.hand = [get_card("Gold"), get_card("Silver")]
    player.coins = 1
    assert player.ai.choose_minion_mode(state, player) == "coins"


def test_courtier_uses_action_to_continue_into_two_type_card():
    state, player = setup()
    player.actions = 0
    player.coins = 0
    player.hand = [get_card("Minion")]
    golds = state.supply["Gold"]
    get_card("Courtier").play_effect(state)
    assert player.actions == 1
    assert player.coins == 3
    assert state.supply["Gold"] == golds


def test_new_forwarding_preserves_default_policies():
    state, player = setup()
    player.ai = GeneticAI(EnhancedStrategy())
    player.hand = [get_card("Estate")] * 3
    assert player.ai.choose_minion_mode(state, player) == AI.choose_minion_mode(
        player.ai, state, player
    )
    options = ["coins", "gold", "action", "buy"]
    assert player.ai.choose_courtier_options(state, player, options, 2) == [
        "coins",
        "gold",
    ]
    assert (
        player.ai.choose_squire_option(state, player, ["actions", "buys", "silver"])
        == "silver"
    )


def test_mandatory_discard_fills_count_and_preserves_useful_cards():
    state, player = setup("old_witch_rabble")
    choices = [get_card(n) for n in ("Rabble", "Gold", "Curse", "Estate", "Copper")]
    assert [
        c.name
        for c in player.ai.choose_cards_to_discard(
            state, player, choices, 3, reason="warehouse"
        )
    ] == ["Curse", "Estate", "Copper"]


def test_soothsayer_gains_curse_to_discard_then_draws_one_card():
    state, player = setup("old_witch_rabble")
    target = state.players[1]
    target.hand = [get_card("Copper") for _ in range(5)]
    target.deck = [get_card("Silver")]
    target.discard = []
    player.discard = []
    get_card("Soothsayer").play_effect(state)
    assert [c.name for c in target.discard] == ["Curse"]
    assert [c.name for c in target.hand] == ["Copper"] * 5 + ["Silver"]
    assert [c.name for c in player.discard] == ["Gold"]


def test_soothsayer_does_not_draw_when_curses_are_empty():
    state, _ = setup("old_witch_rabble")
    target = state.players[1]
    target.hand = []
    target.deck = [get_card("Silver")]
    state.supply["Curse"] = 0
    get_card("Soothsayer").play_effect(state)
    assert target.hand == []
    assert [c.name for c in target.deck] == ["Silver"]


def test_squire_supplies_actions_for_draw_instead_of_stranding_it():
    state, player = setup("old_witch_rabble")
    player.actions = 0
    player.hand = [get_card("Old Witch"), get_card("Rabble")]
    get_card("Squire").on_play(state)
    assert player.actions == 2
    assert player.coins == 1


def test_match_is_repeatable_and_seat_balanced():
    task = ("sentry_hunting_party", {"targets": [["Hunting Party", 2]]}, {}, 4, 98765)
    first = match(task)
    assert match(task) == first
    assert len(first["pair_points"]) == 2
    assert first["truncated"] == 0
    with pytest.raises(ValueError, match="even"):
        match((*task[:3], 3, task[-1]))


@pytest.mark.parametrize("board", KINGDOMS)
def test_published_factory_is_the_policy_used_in_held_out_games(board):
    rows = json.loads(
        Path(f"scripts/data/three_unused_kingdoms/{board}_validate.json").read_text()
    )
    strategy = StrategyLoader().get_strategy(f"{board}_best_found")
    assert strategy is not None
    assert strategy.board == board
    assert all(
        strategy.params == UnusedKingdomPolicy(board, **row["a"]).params for row in rows
    )
    assert all(row["truncated"] == 0 for row in rows)
