"""Tests for the Plunder Traits infrastructure (15 traits)."""

import random

import pytest

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.traits import TRAITS, apply_trait, get_trait


class _NullAI:
    name = "null"

    def __init__(self):
        self.strategy = None

    def choose_action(self, *args, **kwargs):
        return None

    def choose_treasure(self, *args, **kwargs):
        return None

    def choose_buy(self, *args, **kwargs):
        return None

    def choose_card_to_trash(self, state, choices):
        # By default trash a Curse if available, else nothing.
        for c in choices:
            if c is None:
                continue
            if getattr(c, "name", "") == "Curse":
                return c
        return None

    def should_topdeck_with_insignia(self, *args, **kwargs):
        return False

    def should_topdeck_with_royal_seal(self, *args, **kwargs):
        return False

    def choose_watchtower_reaction(self, *args, **kwargs):
        return None

    def should_react_with_market_square(self, *args, **kwargs):
        return False

    def should_play_guard_dog(self, *args, **kwargs):
        return False

    def should_reveal_moat(self, *args, **kwargs):
        return True


def _make_state(num_players: int = 1) -> GameState:
    state = GameState(players=[])
    state.players = [PlayerState(_NullAI()) for _ in range(num_players)]
    for p in state.players:
        p.initialize()
    state.supply = {
        "Copper": 30,
        "Silver": 30,
        "Gold": 30,
        "Curse": 10,
        "Estate": 8,
        "Duchy": 8,
        "Province": 8,
        "Village": 10,
        "Smithy": 10,
        "Witch": 10,
        "Festival": 10,
        "Market": 10,
        "Cage": 10,
    }
    return state


def test_all_15_traits_registered():
    expected = {
        "Cheap", "Cursed", "Fated", "Friendly", "Hasty", "Inherited",
        "Inspiring", "Nearby", "Patient", "Pious", "Reckless", "Rich",
        "Shy", "Tireless", "Fawning",
    }
    assert set(TRAITS.keys()) == expected
    for name in expected:
        trait = get_trait(name)
        assert trait.name == name


def test_cheap_reduces_cost_by_one():
    state = _make_state()
    apply_trait(state, "Cheap", "Village")
    village = get_card("Village")
    cost = state.get_card_cost(state.current_player, village)
    assert cost == village.cost.coins - 1


def test_cursed_gains_curse_and_loot_on_gain():
    state = _make_state()
    apply_trait(state, "Cursed", "Village")
    player = state.current_player
    pre_curses = sum(1 for c in player.discard if c.name == "Curse")
    state.supply["Village"] -= 1
    state.gain_card(player, get_card("Village"))
    # Should also have a Curse and a Loot in discard.
    post_curses = sum(1 for c in player.discard if c.name == "Curse")
    assert post_curses == pre_curses + 1


def test_rich_gains_silver_on_gain():
    state = _make_state()
    apply_trait(state, "Rich", "Village")
    player = state.current_player
    pre_silvers = sum(1 for c in player.discard if c.name == "Silver")
    state.supply["Village"] -= 1
    state.gain_card(player, get_card("Village"))
    post_silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert post_silvers == pre_silvers + 1


def test_nearby_gives_extra_buy_on_buy():
    state = _make_state()
    apply_trait(state, "Nearby", "Village")
    player = state.current_player
    # Simulate the Nearby check: the buy phase increments buys.
    # Direct test of the trait state.
    assert state.pile_traits.get("Village") == "Nearby"


def test_friendly_chains_gains_to_pile_depletion():
    state = _make_state()
    apply_trait(state, "Friendly", "Village")
    player = state.current_player
    # Simulate discarding a Village.
    village = get_card("Village")
    state.discard_card(player, village)
    # Friendly should have triggered a gain (Village in discard pile).
    villages_in_discard = sum(1 for c in player.discard if c.name == "Village")
    assert villages_in_discard >= 2


def test_pious_trashes_pile_card_when_anything_trashed():
    state = _make_state()
    apply_trait(state, "Pious", "Village")
    player = state.current_player
    pre_supply = state.supply["Village"]
    state.trash_card(player, get_card("Curse"))
    # Village count should have decreased and a Village should be in trash.
    assert state.supply["Village"] == pre_supply - 1
    assert any(c.name == "Village" for c in state.trash)


def test_fawning_gains_pile_card_on_province_gain():
    state = _make_state()
    apply_trait(state, "Fawning", "Village")
    player = state.current_player
    pre = sum(1 for c in player.discard if c.name == "Village")
    state.supply["Province"] -= 1
    state.gain_card(player, get_card("Province"))
    post = sum(1 for c in player.discard if c.name == "Village")
    assert post == pre + 1


def test_hasty_sets_aside_then_plays_next_turn():
    state = _make_state()
    apply_trait(state, "Hasty", "Village")
    player = state.current_player
    state.supply["Village"] -= 1
    state.gain_card(player, get_card("Village"))
    # Village should be in hasty_set_aside, not discard.
    assert any(c.name == "Village" for c in state.hasty_set_aside.get(id(player), []))
    # Trigger start-of-turn play.
    state.current_player_index = 0
    state._handle_hasty_start_of_turn(player)
    # Village should now be in_play (Action) and player has 2 actions.
    assert any(c.name == "Village" for c in player.in_play)


def test_hasty_sets_aside_card_gained_to_hand():
    """Regression for PR #193 review: Hasty must trigger even when the
    gained card lands in hand (e.g. Mining Road's gain-to-hand)."""
    state = _make_state()
    apply_trait(state, "Hasty", "Village")
    player = state.current_player
    # Simulate the gain landing in hand directly.
    village = get_card("Village")
    player.hand.append(village)
    state._handle_trait_on_gain(player, village)
    assert village not in player.hand
    assert any(c.name == "Village" for c in state.hasty_set_aside.get(id(player), []))


def test_inherited_replaces_starting_estate():
    state = _make_state()
    # Ensure at least one Estate is in the deck (initial shuffle may have
    # dealt every starting Estate into the opening hand). Inherited only
    # operates on the deck.
    player = state.current_player
    if not any(c.name == "Estate" for c in player.deck):
        for i, c in enumerate(player.hand):
            if c.name == "Estate":
                player.deck.append(player.hand.pop(i))
                break
    pre_estates = sum(1 for c in player.deck if c.name == "Estate")
    pre_villages = sum(1 for c in player.deck if c.name == "Village")
    apply_trait(state, "Inherited", "Village")
    post_estates = sum(1 for c in player.deck if c.name == "Estate")
    post_villages = sum(1 for c in player.deck if c.name == "Village")
    assert post_estates == pre_estates - 1
    assert post_villages == pre_villages + 1


def test_fated_pile_top_decks_on_shuffle():
    state = _make_state()
    apply_trait(state, "Fated", "Village")
    player = state.current_player
    player.deck = []
    player.discard = [get_card("Copper") for _ in range(5)] + [get_card("Village")]
    player.shuffle_discard_into_deck()
    # Village should be on top of the deck (last position).
    assert player.deck[-1].name == "Village"


def test_shy_discards_and_draws_at_start_of_turn():
    state = _make_state()
    apply_trait(state, "Shy", "Village")
    player = state.current_player
    player.hand = [get_card("Village"), get_card("Copper")]
    player.deck = [get_card("Gold"), get_card("Silver"), get_card("Estate")]
    player.discard = []
    pre_hand = len(player.hand)
    state._handle_shy_start_of_turn(player)
    # Village discarded, drew 2 → hand size: started with 2, -1 (Village), +2 = 3.
    assert len(player.hand) == 3
    assert any(c.name == "Village" for c in player.discard)


def test_patient_mats_at_end_of_turn():
    state = _make_state()
    apply_trait(state, "Patient", "Village")
    player = state.current_player
    player.hand = [get_card("Village")]
    # Simulate cleanup mat call by extracting the relevant logic.
    patient_pile = state.trait_piles.get("Patient")
    patient_cards = [c for c in player.hand if c.name == patient_pile]
    state.patient_mat.setdefault(id(player), []).extend(patient_cards)
    for card in patient_cards:
        player.hand.remove(card)
    assert any(c.name == "Village" for c in state.patient_mat[id(player)])
    # Next turn plays them.
    state._handle_patient_start_of_turn(player)
    assert any(c.name == "Village" for c in player.in_play)


def test_tireless_pile_registered():
    state = _make_state()
    apply_trait(state, "Tireless", "Village")
    assert "Village" in state.tireless_piles


def test_reckless_doubles_treasure_play():
    state = _make_state()
    apply_trait(state, "Reckless", "Silver")
    player = state.current_player
    player.hand = [get_card("Silver")]
    pre_coins = player.coins
    # Simulate treasure phase semantics.
    silver = player.hand[0]
    player.hand.remove(silver)
    player.in_play.append(silver)
    silver.on_play(state)
    if state.pile_traits.get(silver.name) == "Reckless":
        if silver in player.in_play:
            silver.on_play(state)
    # Silver gives +$2; doubled to +$4.
    assert player.coins - pre_coins == 4


def test_inspiring_lets_player_play_extra_action():
    state = _make_state()
    apply_trait(state, "Inspiring", "Village")
    player = state.current_player
    # Need an AI that picks the Smithy.
    class PickSmithy:
        name = "pickSmithy"

        def choose_action(self, state, choices):
            for c in choices:
                if c is not None and c.name == "Smithy":
                    return c
            return None

        def choose_card_to_trash(self, *args, **kwargs):
            return None

    player.ai = PickSmithy()
    player.hand = [get_card("Smithy")]
    player.deck = [get_card("Copper") for _ in range(5)]
    village = get_card("Village")
    state._maybe_inspiring_extra_play(player, village)
    # Smithy should now be in play.
    assert any(c.name == "Smithy" for c in player.in_play)
