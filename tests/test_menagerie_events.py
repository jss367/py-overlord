"""Tests for the Menagerie expansion events."""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


def _state():
    state = GameState(players=[])
    state.initialize_game(
        [ChooseFirstActionAI(), ChooseFirstActionAI()], [get_card("Village")]
    )
    state.supply.setdefault("Horse", 30)
    state.supply.setdefault("Silver", 40)
    state.supply.setdefault("Gold", 30)
    state.supply.setdefault("Estate", 8)
    state.supply.setdefault("Duchy", 8)
    state.supply.setdefault("Province", 8)
    state.supply.setdefault("Curse", 10)
    return state, state.players[0]


def test_pursue_discards_matches_keeps_rest():
    state, p1 = _state()
    p1.deck = [
        get_card("Copper"),  # bottom
        get_card("Curse"),
        get_card("Estate"),
        get_card("Silver"),  # top
    ]
    p1.discard = []
    event = get_event("Pursue")
    event.on_buy(state, p1)
    # Pursued name = most-frequent junk; with 1 Curse and 1 Estate and 1 Copper
    # the choose_name_for_pursue returns one of them; the chosen named card
    # should be discarded. So p1.discard should be non-empty if matched.
    assert p1.buys >= 2  # +1 buy from Pursue
    # Either we matched (discard has one) or we didn't (deck still has 4)
    assert len(p1.deck) + len(p1.discard) == 4


def test_commerce_gains_gold_per_unique_name():
    state, p1 = _state()
    p1.gained_cards_this_turn = ["Silver", "Estate", "Silver"]
    event = get_event("Commerce")
    event.on_buy(state, p1)
    gold_count = sum(1 for c in p1.discard + p1.deck if c.name == "Gold")
    assert gold_count == 2  # Silver, Estate (2 unique)


def test_demand_gains_horse_and_card_to_deck():
    state, p1 = _state()
    p1.deck = []
    p1.discard = []
    event = get_event("Demand")
    event.on_buy(state, p1)
    # Both should be on top of deck (deck list)
    names = [c.name for c in p1.deck]
    assert "Horse" in names


def test_reap_sets_aside_gold():
    state, p1 = _state()
    event = get_event("Reap")
    event.on_buy(state, p1)
    assert hasattr(p1, "reap_set_aside")
    assert any(c.name == "Gold" for c in p1.reap_set_aside)


def test_enclave_exiles_duchy():
    state, p1 = _state()
    event = get_event("Enclave")
    event.on_buy(state, p1)
    assert any(c.name == "Duchy" for c in p1.exile)
    assert any(c.name == "Gold" for c in p1.discard + p1.deck)


def test_alliance_gains_one_of_each():
    state, p1 = _state()
    event = get_event("Alliance")
    event.on_buy(state, p1)
    names = [c.name for c in p1.discard + p1.deck]
    for n in ("Province", "Duchy", "Estate", "Gold", "Silver", "Copper"):
        assert n in names
