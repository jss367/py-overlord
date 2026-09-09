"""Rules and setup checks for the randomly drawn ten-pile kingdom."""

from collections import Counter

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.allies.registry import get_ally
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.unused_cards_shepherd import (
    UnusedCardsShepherd,
    create_random_kingdom_shepherd_embassy_money,
)


def board_state(players=2):
    board = load_board("boards/random_unused_card_kingdom.txt")
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(
        [GeneticAI(UnusedCardsShepherd()) for _ in range(players)],
        [get_card(n) for n in board.kingdom_cards],
        allies=[get_ally(n) for n in board.allies],
    )
    return state


@pytest.mark.parametrize("players,expected", [(2, 8), (3, 12), (4, 12)])
def test_fairgrounds_uses_victory_pile_size(players, expected):
    assert board_state(players).supply["Fairgrounds"] == expected


def test_random_kingdom_has_heirloom_potion_and_complete_forts():
    state = board_state()
    assert state.supply["Potion"] == 16
    assert "Colony" not in state.supply
    assert "Platinum" not in state.supply
    for player in state.players:
        assert Counter(c.name for c in player.all_cards()) == {
            "Copper": 6,
            "Pasture": 1,
            "Estate": 3,
        }
    assert state.top_supply_card("Tent") == "Tent"
    assert all(
        state.supply[n] == 4 for n in ("Tent", "Garrison", "Hill Fort", "Stronghold")
    )


def test_bauble_strategy_requests_favor_then_extra_buy():
    state = board_state()
    player = state.current_player
    player.favors = 0
    player.coins = 0
    player.buys = 1
    get_card("Bauble").on_play(state)
    assert (player.favors, player.coins, player.buys) == (1, 1, 1)
    get_card("Bauble").on_play(state)
    assert (player.favors, player.coins, player.buys) == (1, 2, 2)


@pytest.mark.parametrize(
    "coins,expected", [(2, "Bauble"), (3, "Silver"), (4, "Shepherd"), (5, "Embassy")]
)
def test_published_strategy_opening_uses_the_affordable_core(coins, expected):
    state = board_state()
    player = state.current_player
    strategy = create_random_kingdom_shepherd_embassy_money()
    choices = [
        get_card(n)
        for n in state.supply
        if get_card(n).cost.coins <= coins
        and not get_card(n).cost.potions
        and get_card(n).may_be_bought(state)
    ]
    assert strategy.choose_gain(state, player, choices).name == expected
    # Unselected search variants must not register false card usage.
    assert "University" not in {r.card for r in strategy.gain_priority}
