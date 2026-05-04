"""Tests for Empires Castles 8-pile."""

import pytest

from dominion.cards.empires.castles import (
    CASTLE_ORDER,
    CrumblingCastle,
    GrandCastle,
    HauntedCastle,
    HumbleCastle,
    KingsCastle,
    OpulentCastle,
    SmallCastle,
    SprawlingCastle,
)
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _make_game(num_players=2):
    players = [PlayerState(DummyAI()) for _ in range(num_players)]
    state = GameState(players=players)
    state.initialize_game(
        [DummyAI() for _ in range(num_players)],
        [get_card("Humble Castle"), get_card("Village")],
    )
    return state


def test_castle_order_is_eight():
    assert len(CASTLE_ORDER) == 8


def test_only_top_castle_buyable():
    state = _make_game(2)

    humble = get_card("Humble Castle")
    crumbling = get_card("Crumbling Castle")
    kings = get_card("King's Castle")

    assert humble.may_be_bought(state)
    assert not crumbling.may_be_bought(state)
    assert not kings.may_be_bought(state)

    # Drain Humble Castle.
    state.supply["Humble Castle"] = 0
    assert crumbling.may_be_bought(state)
    assert not kings.may_be_bought(state)


def test_castle_supply_setup_two_player():
    state = _make_game(2)
    for name in CASTLE_ORDER:
        assert state.supply[name] == 1


def test_castle_supply_setup_three_player():
    state = _make_game(3)
    for name in CASTLE_ORDER:
        assert state.supply[name] == 2


def test_humble_castle_vp_per_castle():
    player = PlayerState(DummyAI())
    player.deck = [get_card("Humble Castle"), get_card("Crumbling Castle"), get_card("King's Castle")]
    humble = HumbleCastle()
    # Humble Castle scores 1 VP per Castle the player has.
    assert humble.get_victory_points(player) == 3


def test_kings_castle_two_vp_per_castle():
    player = PlayerState(DummyAI())
    player.deck = [get_card("Humble Castle"), get_card("King's Castle"), get_card("Sprawling Castle")]
    kings = KingsCastle()
    assert kings.get_victory_points(player) == 6


def test_crumbling_castle_on_gain_grants_vp_token_and_silver():
    state = _make_game(2)
    player = state.players[0]
    crumbling = CrumblingCastle()
    silver_before = state.supply.get("Silver", 0)
    state.gain_card(player, crumbling)
    assert player.vp_tokens >= 1
    assert state.supply["Silver"] == silver_before - 1


def test_haunted_castle_on_gain_grants_gold_and_attacks():
    state = _make_game(2)
    player = state.players[0]
    other = state.players[1]
    # Stuff opponent's hand with 5 cards.
    other.hand = [get_card("Copper") for _ in range(5)]

    gold_before = state.supply.get("Gold", 0)
    haunted = HauntedCastle()
    state.gain_card(player, haunted)
    assert state.supply["Gold"] == gold_before - 1
    # Two cards should be on top of opponent's deck.
    assert len(other.hand) == 3
    assert len(other.deck) >= 2


def test_grand_castle_grants_vp_per_victory_in_hand_and_play():
    state = _make_game(2)
    player = state.players[0]
    player.hand = [get_card("Estate"), get_card("Province")]
    player.in_play = [get_card("Duchy")]
    grand = GrandCastle()
    state.gain_card(player, grand)
    # 3 victory cards visible -> +3 VP tokens.
    assert player.vp_tokens >= 3


def test_sprawling_castle_grants_estates_or_duchy():
    state = _make_game(2)
    player = state.players[0]
    sprawling = SprawlingCastle()
    estates_before = state.supply["Estate"]
    state.gain_card(player, sprawling)
    # We have plenty of Estates so 3 should be gained.
    assert state.supply["Estate"] == estates_before - 3


def test_opulent_castle_discard_for_coins():
    state = _make_game(2)
    player = state.players[0]
    opulent = OpulentCastle()
    player.in_play.append(opulent)
    player.hand = [get_card("Estate"), get_card("Duchy"), get_card("Copper")]
    coins_before = player.coins
    opulent.play_effect(state)
    # Two victory cards discarded -> +$4.
    assert player.coins == coins_before + 4
    assert all(c.name == "Copper" for c in player.hand)


def test_castles_count_as_single_pile_for_empty_piles():
    """Emptying individual Castle ranks must not trip the "three piles
    depleted" game-end condition. All 8 Castle cards collapse to one pile."""
    state = _make_game(2)

    # Drain the first three Castle ranks. Castles as a whole still have
    # cards, so empty_piles should not count any of them.
    for name in CASTLE_ORDER[:3]:
        state.supply[name] = 0
    assert state.empty_piles == 0

    # Drain everything but King's Castle: still not "Castles empty".
    for name in CASTLE_ORDER[:-1]:
        state.supply[name] = 0
    assert state.empty_piles == 0

    # Drain the final Castle: now Castles counts as one empty pile.
    state.supply[CASTLE_ORDER[-1]] = 0
    assert state.empty_piles == 1


def test_small_castle_trash_self_gains_castle():
    state = _make_game(2)
    player = state.players[0]
    small = SmallCastle()
    player.in_play.append(small)

    # Pile setup: Humble Castle is top in 2P with 1 copy.
    assert state.supply["Humble Castle"] == 1
    small.play_effect(state)
    # Small Castle should be trashed; player should have gained Humble Castle.
    assert state.supply["Humble Castle"] == 0
    assert any(c.name == "Humble Castle" for c in player.discard + player.hand + player.deck)
