"""Tests for the Marchland promo card and the Summon promo event."""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


def _new_state(kingdom_card_names=None):
    if kingdom_card_names is None:
        kingdom_card_names = ["Village", "Smithy"]
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card(n) for n in kingdom_card_names])
    return state


# --- Marchland --------------------------------------------------------------


def test_marchland_gives_buy_and_dollars_for_discards():
    state = _new_state()
    player = state.players[0]
    player.hand = [get_card("Copper"), get_card("Estate"), get_card("Curse")]
    starting_buys = player.buys
    starting_coins = player.coins

    marchland = get_card("Marchland")
    player.in_play.append(marchland)
    marchland.on_play(state)

    assert player.buys == starting_buys + 1
    # All three default-low-priority cards should be discarded for $3.
    assert player.coins == starting_coins + 3
    assert player.hand == []
    discarded_names = sorted(c.name for c in player.discard)
    assert discarded_names == ["Copper", "Curse", "Estate"]


def test_marchland_with_empty_hand_just_gives_buy():
    state = _new_state()
    player = state.players[0]
    player.hand = []
    starting_buys = player.buys
    starting_coins = player.coins

    marchland = get_card("Marchland")
    player.in_play.append(marchland)
    marchland.on_play(state)

    assert player.buys == starting_buys + 1
    assert player.coins == starting_coins


def test_marchland_vp_is_one_per_three_victory_cards():
    state = _new_state()
    player = state.players[0]
    marchland = get_card("Marchland")
    # Replace deck with a controlled set: 7 victory cards + non-victory.
    player.hand = []
    player.discard = []
    player.in_play = []
    player.deck = (
        [get_card("Estate") for _ in range(4)]
        + [get_card("Duchy") for _ in range(2)]
        + [get_card("Province")]
        + [get_card("Copper") for _ in range(5)]
        + [marchland]  # Marchland itself counts (it's a Victory card).
    )
    # 4 + 2 + 1 + 1 (Marchland) = 8 victory cards => 8 // 3 = 2 VP.
    assert marchland.get_victory_points(player) == 2


def test_marchland_zero_vp_with_two_victory_cards():
    state = _new_state()
    player = state.players[0]
    marchland = get_card("Marchland")
    player.hand = []
    player.discard = []
    player.in_play = []
    # 1 Estate + Marchland = 2 victory cards => 2 // 3 = 0 VP.
    player.deck = [get_card("Estate"), marchland]
    assert marchland.get_victory_points(player) == 0


def test_marchland_is_action_and_victory():
    marchland = get_card("Marchland")
    assert marchland.is_action
    assert marchland.is_victory


# --- Summon -----------------------------------------------------------------


def test_summon_gains_action_and_sets_aside_for_next_turn():
    state = _new_state(["Village"])
    player = state.players[0]
    summon = get_event("Summon")
    summon.on_buy(state, player)

    # Card is set aside, NOT in discard or deck.
    assert len(player.summon_set_aside) == 1
    set_aside = player.summon_set_aside[0]
    assert set_aside.is_action
    assert set_aside.cost.coins <= 4
    assert set_aside not in player.discard
    assert set_aside not in player.deck


def test_summon_skips_when_no_legal_action_in_supply():
    # A kingdom with no <=$4 Action: Smithy is $4, so include something
    # cheap-but-not-action only by suppressing supply.
    state = _new_state(["Smithy"])
    player = state.players[0]
    # Empty out every Action <= $4 from the supply.
    for name in list(state.supply.keys()):
        try:
            card = get_card(name)
        except Exception:
            continue
        if card.is_action and card.cost.coins <= 4:
            state.supply[name] = 0
    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert player.summon_set_aside == []


def test_summon_set_aside_card_plays_on_next_turn_start():
    state = _new_state(["Village"])
    player = state.players[0]
    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert len(player.summon_set_aside) == 1
    set_aside = player.summon_set_aside[0]
    assert set_aside.name == "Village"

    # Drive a fresh start phase as if the next turn had begun.
    starting_actions = player.actions
    starting_hand_len = len(player.hand)
    state.phase = "start"
    state.handle_start_phase()

    # Village played: +1 Card, +2 Actions; the card lives in in_play now.
    assert player.summon_set_aside == []
    assert set_aside in player.in_play
    assert player.actions == starting_actions + 2
    assert len(player.hand) == starting_hand_len + 1


def test_summon_decrements_supply():
    state = _new_state(["Village"])
    player = state.players[0]
    before = state.supply["Village"]
    summon = get_event("Summon")
    summon.on_buy(state, player)
    after = state.supply["Village"]
    assert after == before - 1


def test_summoned_card_is_owned_by_player_for_scoring():
    state = _new_state(["Village"])
    player = state.players[0]
    summon = get_event("Summon")
    summon.on_buy(state, player)
    set_aside = player.summon_set_aside[0]
    # The set-aside zone is part of the player's owned cards.
    assert set_aside in player.all_cards()
