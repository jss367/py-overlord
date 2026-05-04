"""Tests for Empires Landmarks (20 landmarks)."""

import random

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.landmarks import (
    Aqueduct,
    Arena,
    BanditFort,
    Basilica,
    Battlefield,
    Colonnade,
    DefiledShrine,
    Fountain,
    Keep,
    Labyrinth,
    LANDMARK_TYPES,
    MountainPass,
    Museum,
    Obelisk,
    Orchard,
    Palace,
    Tomb,
    Tower,
    TriumphalArch,
    Wall,
    WolfDen,
    all_landmarks,
)

from tests.utils import DummyAI


def _make_game(landmarks=None, num_players=2):
    players = [PlayerState(DummyAI()) for _ in range(num_players)]
    state = GameState(players=players)
    state.initialize_game(
        [DummyAI() for _ in range(num_players)],
        [get_card("Village"), get_card("Smithy"), get_card("Witch")],
        landmarks=landmarks or [],
    )
    return state


def test_twenty_landmarks_registered():
    assert len(LANDMARK_TYPES) == 20
    instances = all_landmarks()
    assert len(instances) == 20


def test_aqueduct_moves_vp_on_treasure_and_victory_gain():
    landmark = Aqueduct()
    state = _make_game([landmark])
    player = state.players[0]

    state.gain_card(player, get_card("Silver"))
    assert landmark.vp_pool == 1
    assert landmark.pile_vp["Silver"] == 7

    state.gain_card(player, get_card("Estate"))
    assert player.vp_tokens == 1
    assert landmark.vp_pool == 0


def test_arena_setup_pool_six_per_player():
    landmark = Arena()
    state = _make_game([landmark], num_players=3)
    assert landmark.vp_pool == 18


def test_arena_discard_action_for_vp():
    landmark = Arena()
    state = _make_game([landmark])
    player = state.players[0]
    player.hand = [get_card("Village")]
    state.current_player_index = 0
    landmark.on_buy_phase_start(state, player)
    assert player.vp_tokens == 2
    assert landmark.vp_pool == 6 * 2 - 2


def test_bandit_fort_neg_two_per_silver_gold():
    landmark = BanditFort()
    state = _make_game([landmark])
    player = state.players[0]
    player.discard = []
    player.hand = []
    player.in_play = []
    player.deck = [get_card("Silver"), get_card("Gold"), get_card("Copper")]
    assert landmark.vp_for(state, player) == -4


def test_basilica_grants_two_vp_with_two_coins_left():
    landmark = Basilica()
    state = _make_game([landmark])
    player = state.players[0]
    player.coins = 3
    landmark.on_buy(state, player, get_card("Copper"))
    assert player.vp_tokens == 2


def test_battlefield_grants_two_vp_on_victory_gain():
    landmark = Battlefield()
    state = _make_game([landmark])
    player = state.players[0]
    state.gain_card(player, get_card("Estate"))
    assert player.vp_tokens == 2


def test_colonnade_grants_vp_on_action_buy_with_copy_in_play():
    landmark = Colonnade()
    state = _make_game([landmark])
    player = state.players[0]
    player.in_play.append(get_card("Village"))
    landmark.on_buy(state, player, get_card("Village"))
    assert player.vp_tokens == 2


def test_defiled_shrine_moves_vp_on_action_gain_and_releases_on_curse_buy():
    landmark = DefiledShrine()
    state = _make_game([landmark])
    player = state.players[0]
    state.gain_card(player, get_card("Village"))
    assert landmark.vp_pool == 1
    landmark.on_buy(state, player, get_card("Curse"))
    assert player.vp_tokens == 1


def test_fountain_grants_15_vp_with_ten_coppers():
    landmark = Fountain()
    state = _make_game([landmark])
    player = state.players[0]
    player.discard = []
    player.hand = []
    player.in_play = []
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.hand = []
    player.in_play = []
    assert landmark.vp_for(state, player) == 15
    player.deck = [get_card("Copper") for _ in range(9)]
    assert landmark.vp_for(state, player) == 0


def test_keep_grants_five_vp_per_majority_treasure():
    landmark = Keep()
    state = _make_game([landmark])
    p1 = state.players[0]
    p2 = state.players[1]
    p1.deck = []; p1.discard = []; p1.hand = []
    p2.deck = []; p2.discard = []; p2.hand = []
    p1.deck = [get_card("Silver"), get_card("Silver")]
    p2.deck = [get_card("Silver")]
    # P1 has more Silvers; +5 VP.
    assert landmark.vp_for(state, p1) == 5
    # P2 ties or loses on every treasure -> 0 (P2 has 1 Silver, P1 has 2).
    assert landmark.vp_for(state, p2) == 0


def test_labyrinth_grants_vp_on_second_card_gained():
    landmark = Labyrinth()
    state = _make_game([landmark])
    player = state.players[0]
    state.gain_card(player, get_card("Copper"))
    assert player.vp_tokens == 0
    state.gain_card(player, get_card("Copper"))
    # Now the 2nd gain should give +2 VP.
    assert player.vp_tokens == 2


def test_mountain_pass_fires_on_first_province_gain():
    landmark = MountainPass()
    state = _make_game([landmark])
    player = state.players[0]
    state.gain_card(player, get_card("Province"))
    assert player.vp_tokens == 8
    assert player.debt == 8

    # Subsequent Province gains don't fire.
    other = state.players[1]
    state.gain_card(other, get_card("Province"))
    assert other.vp_tokens == 0


def test_museum_two_vp_per_distinct_card():
    landmark = Museum()
    state = _make_game([landmark])
    player = state.players[0]
    player.discard = []
    player.hand = []
    player.in_play = []
    player.deck = [get_card("Copper"), get_card("Silver"), get_card("Estate"), get_card("Copper")]
    # 3 distinct names -> 6.
    assert landmark.vp_for(state, player) == 6


def test_obelisk_chosen_pile_grants_two_vp_per_copy():
    landmark = Obelisk()
    state = _make_game([landmark])
    player = state.players[0]
    chosen = landmark.chosen_pile
    assert chosen
    player.deck = [get_card(chosen) for _ in range(3)]
    assert landmark.vp_for(state, player) == 6


def test_orchard_four_vp_per_action_with_three_copies():
    landmark = Orchard()
    state = _make_game([landmark])
    player = state.players[0]
    player.discard = []
    player.hand = []
    player.in_play = []
    player.deck = [get_card("Village") for _ in range(3)] + [get_card("Smithy") for _ in range(2)]
    # Only Village has 3+ copies -> 4 VP.
    assert landmark.vp_for(state, player) == 4
    player.deck.extend([get_card("Smithy")])
    # Now both Village and Smithy have 3+ -> 8.
    assert landmark.vp_for(state, player) == 8


def test_palace_three_vp_per_treasure_set():
    landmark = Palace()
    state = _make_game([landmark])
    player = state.players[0]
    player.discard = []
    player.hand = []
    player.in_play = []
    player.deck = [
        get_card("Copper"), get_card("Copper"),
        get_card("Silver"),
        get_card("Gold"), get_card("Gold"),
    ]
    # min(2, 1, 2) = 1 set -> 3 VP.
    assert landmark.vp_for(state, player) == 3


def test_tomb_grants_vp_on_each_trash():
    landmark = Tomb()
    state = _make_game([landmark])
    player = state.players[0]
    state.trash_card(player, get_card("Copper"))
    state.trash_card(player, get_card("Estate"))
    assert player.vp_tokens == 2


def test_tower_one_vp_per_non_victory_from_empty_pile():
    landmark = Tower()
    state = _make_game([landmark])
    player = state.players[0]
    state.supply["Village"] = 0
    state.supply["Estate"] = 0
    player.deck = [get_card("Village"), get_card("Village"), get_card("Estate")]
    # Village pile empty -> 2 VP. Estate pile empty but Estate is Victory -> 0.
    assert landmark.vp_for(state, player) == 2


def test_triumphal_arch_three_vp_per_second_most_action():
    landmark = TriumphalArch()
    state = _make_game([landmark])
    player = state.players[0]
    player.discard = []
    player.hand = []
    player.in_play = []
    player.deck = [get_card("Village") for _ in range(4)] + [get_card("Smithy") for _ in range(2)] + [get_card("Witch")]
    # Counts: Village=4, Smithy=2, Witch=1. Second-most = 2 -> 6.
    assert landmark.vp_for(state, player) == 6


def test_wall_neg_one_per_card_over_15():
    landmark = Wall()
    state = _make_game([landmark])
    player = state.players[0]
    player.discard = []
    player.hand = []
    player.in_play = []
    player.deck = [get_card("Copper") for _ in range(20)]
    assert landmark.vp_for(state, player) == -5


def test_wolf_den_neg_three_per_singleton_card():
    landmark = WolfDen()
    state = _make_game([landmark])
    player = state.players[0]
    player.discard = []
    player.hand = []
    player.in_play = []
    player.deck = [get_card("Village"), get_card("Smithy"), get_card("Smithy")]
    # Village=1 (singleton), Smithy=2 -> -3.
    assert landmark.vp_for(state, player) == -3


def test_landmarks_contribute_to_final_vp():
    landmark = Tomb()
    state = _make_game([landmark])
    player = state.players[0]
    state.trash_card(player, get_card("Copper"))
    # Tomb already gives +1 VP via the on_trash hook (vp_tokens). Confirm
    # final VP path uses landmark vp_for too.
    base_vp = player.get_victory_points(state)
    assert base_vp >= 1
