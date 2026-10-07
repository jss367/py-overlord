"""Printed-rule regressions required for the Shepherd/Tragic Hero search."""

from collections import Counter

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.strategies.shepherd_tragic_hero import (
    KINGDOM,
    ShepherdTragicHero,
)
from tests.utils import TrashFirstAI


def setup(ai=None):
    state = GameState(
        players=[PlayerState(ai or TrashFirstAI())],
        supply={
            "Gold": 30,
            "Silver": 40,
            "Estate": 8,
            "Province": 8,
            "Shepherd": 10,
            "Secret Cave": 10,
            "Wish": 12,
            "Will-o'-Wisp": 12,
            "Imp": 13,
            "Ghost": 6,
        },
    )
    state.log_callback = lambda *_: None
    return state, state.current_player


@pytest.mark.parametrize(
    "trash,gain", [("Estate", "Will-o'-Wisp"), ("Silver", "Imp"), ("Gold", "Ghost")]
)
def test_exorcist_gains_only_a_cheaper_spirit(trash, gain):
    state, player = setup()
    player.hand = [get_card(trash)]
    get_card("Exorcist").play_effect(state)
    assert [c.name for c in state.trash] == [trash]
    assert [c.name for c in player.discard] == [gain]


def test_crypt_sets_aside_played_gold_and_preserves_ownership():
    state, player = setup(GeneticAI(ShepherdTragicHero(crypt=1)))
    crypt, gold, silver = map(get_card, ["Crypt", "Gold", "Silver"])
    player.in_play = [crypt, gold]
    player.hand = [silver]
    player.actions = 0
    crypt.on_play(state)
    assert crypt.set_aside == [gold]
    assert gold not in player.in_play
    assert silver in player.hand
    assert gold in player.all_cards()
    assert player.actions == 0
    crypt.on_duration(state)
    assert gold in player.hand
    assert not crypt.duration_persistent


def test_lamp_requires_singletons_and_counts_duration_cards():
    state, player = setup()
    lamp = get_card("Magic Lamp")
    player.in_play = [lamp] + [
        get_card(n)
        for n in ["Copper", "Copper", "Silver", "Gold", "Pasture", "Shepherd"]
    ]
    lamp.on_play(state)
    assert lamp not in state.trash
    # Six singletons now, including the Guardian retained from last turn.
    player.duration = [get_card("Guardian")]
    lamp.on_play(state)
    assert lamp in state.trash
    assert state.supply["Wish"] == 9


def test_guardian_is_gained_to_hand():
    state, player = setup()
    guardian = state.gain_card(player, get_card("Guardian"))
    assert guardian in player.hand
    assert guardian not in player.discard


def test_ghost_plays_twice_next_turn_and_keeps_set_aside_card_owned():
    state, player = setup()
    ghost, hero = map(get_card, ["Ghost", "Tragic Hero"])
    player.in_play = [ghost]
    player.deck = [get_card("Copper") for _ in range(12)] + [hero]
    player.hand = [get_card("Copper") for _ in range(5)]
    ghost.on_play(state)
    assert hero in player.all_cards()
    state.do_duration_phase()
    assert len(player.hand) == 11
    assert player.buys == 3
    assert state.trash.count(hero) == 1
    assert sum(c.name == "Gold" for c in player.discard) == 2
    assert not ghost.set_aside


def test_wish_cannot_gain_twice_when_replayed():
    state, player = setup()
    wish = get_card("Wish")
    player.in_play = [wish]
    wish.on_play(state)
    wish.on_play(state)
    assert state.supply["Wish"] == 13
    assert state.supply["Gold"] == 29


def test_repeated_cave_accumulates_bonuses():
    state, player = setup()
    cave = get_card("Secret Cave")
    player.in_play = [cave]
    player.hand = [get_card("Estate") for _ in range(6)]
    cave.play_effect(state)
    cave.play_effect(state)
    cave.play_effect(state)  # Declining a third discard must preserve both.
    cave.on_duration(state)
    assert player.coins == 6


def test_board_initializes_both_heirlooms_and_all_extra_piles():
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(
        [TrashFirstAI(), TrashFirstAI()], [get_card(n) for n in KINGDOM]
    )
    for player in state.players:
        assert Counter(c.name for c in player.all_cards()) == {
            "Copper": 5,
            "Estate": 3,
            "Magic Lamp": 1,
            "Pasture": 1,
        }
    assert state.supply["Wish"] == 12
    assert {"Wish", "Will-o'-Wisp", "Imp", "Ghost"} <= state.non_supply_pile_names


def test_zero_shepherd_target_does_not_buy_it_in_opening():
    strategy = ShepherdTragicHero(shepherd=0, monastery=0)
    state, player = setup(GeneticAI(strategy))
    player.turns_taken = 1
    choices = [get_card("Shepherd"), get_card("Silver"), None]
    assert player.ai.choose_buy(state, choices).name == "Silver"


def test_monastery_stops_trashing_useful_cards():
    state, player = setup(GeneticAI(ShepherdTragicHero()))
    player.hand = [get_card("Gold"), get_card("Pasture"), get_card("Estate")]
    assert (
        player.ai.choose_cards_to_trash_for_monastery(state, player, player.hand, 3)
        == []
    )


def test_hound_is_owned_while_set_aside():
    state, player = setup()
    hound = get_card("Faithful Hound")
    state.discard_card(player, hound)
    assert hound in player.all_cards()


def test_search_pairs_both_seats_and_is_reproducible():
    from scripts.search_shepherd_tragic_hero import match

    spec = dict(shepherd=1, hero=1, monastery=0, silver=99)
    first = match((spec, spec, 4, 901))
    assert first == match((spec, spec, 4, 901))
    assert first["rate"] == 0.5
    assert first["paired_scores"] == [0.5, 0.5]
    assert first["truncated"] == 0



def test_magic_lamp_does_not_count_astrolabe_trashed_by_counterfeit():
    state, player = setup()
    lamp, counterfeit, astrolabe = map(get_card, ["Magic Lamp", "Counterfeit", "Astrolabe"])
    player.ai.should_replay_treasure_with_counterfeit = lambda *_: astrolabe
    player.hand = [astrolabe]
    player.in_play = [counterfeit] + [get_card(n) for n in ["Copper", "Silver", "Gold"]]
    counterfeit.on_play(state)
    assert astrolabe in player.duration
    assert astrolabe in state.trash
    player.in_play.append(lamp)
    lamp.on_play(state)
    assert lamp not in state.trash
    assert state.supply["Wish"] == 12


@pytest.mark.parametrize("zone", ["hand", "deck", "discard", "exile", "tavern_mat"])
def test_magic_lamp_does_not_count_duration_moved_to_another_zone(zone):
    state, player = setup()
    lamp, guardian = map(get_card, ["Magic Lamp", "Guardian"])
    player.in_play = [lamp] + [get_card(n) for n in ["Copper", "Silver", "Gold", "Shepherd"]]
    player.duration = [guardian]
    getattr(player, zone).append(guardian)
    lamp.on_play(state)
    assert lamp not in state.trash
    assert state.supply["Wish"] == 12
