"""Tests for Nocturne Boons infrastructure and each individual Boon."""

from dominion.boons import (
    BOON_EFFECTS,
    PERSISTENT_BOONS,
    create_boons_deck,
    is_persistent_boon,
    resolve_boon,
)
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class _GainAllAI(DummyAI):
    def choose_card_to_gain_up_to(self, state, player, choices, max_cost):
        return max(choices, key=lambda c: (c.cost.coins, c.name))

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c.name == "Estate":
                return c
        return choices[0] if choices else None

    def choose_card_to_topdeck_from_discard(self, state, player, choices):
        return choices[0] if choices else None

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        return choices[:count]

    def order_cards_for_topdeck(self, state, player, cards):
        return list(cards)

    def choose_treasure_to_discard_for_earths_gift(self, state, player, treasures):
        return min(treasures, key=lambda c: (c.cost.coins, c.name))


def _setup_state(ai=None):
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.players = [PlayerState(ai or _GainAllAI())]
    state.players[0].initialize()
    state.supply = {
        "Copper": 30, "Silver": 20, "Gold": 10, "Curse": 10,
        "Estate": 10, "Duchy": 10, "Province": 8,
        "Will-o'-Wisp": 12,
    }
    return state, state.players[0]


def test_create_boons_deck_has_all_twelve():
    deck = create_boons_deck()
    assert len(deck) == 12
    assert set(deck) == set(BOON_EFFECTS.keys())


def test_is_persistent_boon():
    assert is_persistent_boon("The Field's Gift")
    assert is_persistent_boon("The Forest's Gift")
    assert is_persistent_boon("The River's Gift")
    assert not is_persistent_boon("The Sea's Gift")
    assert PERSISTENT_BOONS == {
        "The Field's Gift",
        "The Forest's Gift",
        "The River's Gift",
    }


def test_earths_gift_discards_treasure_and_gains():
    state, player = _setup_state()
    player.hand = [get_card("Copper"), get_card("Estate")]
    resolve_boon("The Earth's Gift", state, player)
    # Copper discarded, gained a card up to $4 (Duchy / Estate / Silver — pick most expensive in supply)
    assert any(c.name == "Copper" for c in player.discard)
    # Should have gained something
    gained = [c for c in player.discard if c.name not in {"Copper"}]
    assert gained


def test_fields_gift_grants_action_and_coin():
    state, player = _setup_state()
    player.actions = 1
    player.coins = 0
    resolve_boon("The Field's Gift", state, player)
    assert player.actions == 2
    assert player.coins == 1


def test_flames_gift_trashes_card():
    state, player = _setup_state()
    player.hand = [get_card("Estate"), get_card("Copper")]
    resolve_boon("The Flame's Gift", state, player)
    assert any(c.name == "Estate" for c in state.trash)


def test_forests_gift_grants_buy_and_coin():
    state, player = _setup_state()
    player.buys = 1
    player.coins = 0
    resolve_boon("The Forest's Gift", state, player)
    assert player.buys == 2
    assert player.coins == 1


def test_moons_gift_topdecks_from_discard():
    state, player = _setup_state()
    player.discard = [get_card("Silver")]
    resolve_boon("The Moon's Gift", state, player)
    assert player.discard == []
    assert player.deck and player.deck[-1].name == "Silver"


def test_mountains_gift_gains_silver():
    state, player = _setup_state()
    silver_before = state.supply["Silver"]
    resolve_boon("The Mountain's Gift", state, player)
    assert state.supply["Silver"] == silver_before - 1
    assert any(c.name == "Silver" for c in player.discard)


def test_rivers_gift_no_immediate_effect():
    state, player = _setup_state()
    initial_hand = list(player.hand)
    resolve_boon("The River's Gift", state, player)
    # No immediate effect
    assert list(player.hand) == initial_hand


def test_seas_gift_draws_one():
    state, player = _setup_state()
    player.hand = []
    player.deck = [get_card("Silver")]
    resolve_boon("The Sea's Gift", state, player)
    assert len(player.hand) == 1


def test_skys_gift_discards_three_for_gold():
    state, player = _setup_state()
    player.hand = [get_card("Copper"), get_card("Estate"), get_card("Curse")]
    gold_before = state.supply["Gold"]
    resolve_boon("The Sky's Gift", state, player)
    assert state.supply["Gold"] == gold_before - 1
    # Hand was discarded
    assert player.hand == []


def test_skys_gift_no_gold_when_under_three_in_hand():
    state, player = _setup_state()
    player.hand = [get_card("Copper")]
    gold_before = state.supply["Gold"]
    resolve_boon("The Sky's Gift", state, player)
    assert state.supply["Gold"] == gold_before


def test_suns_gift_filters_top_four():
    state, player = _setup_state()
    player.deck = [get_card("Silver"), get_card("Estate"), get_card("Gold"), get_card("Curse")]
    resolve_boon("The Sun's Gift", state, player)
    # Default AI discards Estate/Curse, keeps Silver and Gold
    discarded_names = {c.name for c in player.discard}
    assert "Estate" in discarded_names
    assert "Curse" in discarded_names


def test_swamps_gift_gains_will_o_wisp():
    state, player = _setup_state()
    wisps_before = state.supply["Will-o'-Wisp"]
    resolve_boon("The Swamp's Gift", state, player)
    assert state.supply["Will-o'-Wisp"] == wisps_before - 1
    assert any(c.name == "Will-o'-Wisp" for c in player.discard)


def test_winds_gift_draws_two_discards_two():
    state, player = _setup_state()
    player.hand = []
    player.deck = [get_card("Silver"), get_card("Gold")]
    resolve_boon("The Wind's Gift", state, player)
    # Drew 2, then discarded 2 → hand empty, discard has 2
    assert len(player.hand) == 0
    assert len(player.discard) == 2


def test_draw_boon_returns_a_name():
    state, _ = _setup_state()
    state.boons_deck = []
    state.boons_discard = []
    boon = state.draw_boon()
    assert boon in BOON_EFFECTS


def test_persistent_boon_remains_active_until_next_turn():
    state, player = _setup_state()
    state.resolve_boon(player, "The Field's Gift")
    assert "The Field's Gift" in player.active_boons
    # discard pile should NOT contain it yet
    assert "The Field's Gift" not in state.boons_discard
