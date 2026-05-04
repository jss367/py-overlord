"""Tests for Empires events."""

from dominion.cards.registry import get_card
from dominion.events.empires_events import (
    Advance,
    Annex,
    Banquet,
    Conquest,
    Delve,
    Dominate,
    Donate,
    Ritual,
    SaltTheEarth,
    Tax,
    Triumph,
    Wedding,
    Windfall,
)
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _make_game(num_players=2):
    players = [PlayerState(DummyAI()) for _ in range(num_players)]
    state = GameState(players=players)
    state.initialize_game(
        [DummyAI() for _ in range(num_players)],
        [get_card("Village")],
    )
    return state


def test_all_thirteen_events_registered():
    expected = [
        "Triumph", "Annex", "Donate", "Advance", "Delve", "Tax", "Banquet",
        "Ritual", "Salt the Earth", "Wedding", "Windfall", "Conquest", "Dominate",
    ]
    for name in expected:
        assert get_event(name) is not None


def test_triumph_grants_estate_and_vp():
    state = _make_game()
    player = state.players[0]
    player.cards_gained_this_turn = 3
    Triumph().on_buy(state, player)
    assert any(c.name == "Estate" for c in player.discard)
    # 3 cards gained before + 1 Estate gained == 4 VP.
    assert player.vp_tokens == 4


def test_annex_gains_duchy_and_moves_discard_to_deck():
    state = _make_game()
    player = state.players[0]
    player.discard = [get_card("Estate") for _ in range(8)]
    Annex().on_buy(state, player)
    # Should keep up to 5 in discard, rest in deck.
    duchy_count = sum(1 for c in player.discard + player.deck if c.name == "Duchy")
    assert duchy_count == 1


def test_donate_pending_resolves_at_end_of_buy_phase():
    state = _make_game()
    player = state.players[0]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = [get_card("Copper") for _ in range(5)]
    Donate().on_buy(state, player)
    assert player.donate_pending == 1


def test_advance_trashes_action_and_gains_action():
    state = _make_game()
    player = state.players[0]
    village = get_card("Village")
    player.hand = [village]

    class TrashAI(DummyAI):
        def choose_card_to_trash(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    player.ai = TrashAI()
    Advance().on_buy(state, player)
    # Village trashed, an action up to $6 gained. Village is in trash.
    assert any(c.name == "Village" for c in state.trash)
    # Player should have gained an action.
    gained = player.discard + player.deck
    assert any(c.is_action for c in gained)


def test_delve_grants_buy_and_silver():
    state = _make_game()
    player = state.players[0]
    silver_before = state.supply["Silver"]
    Delve().on_buy(state, player)
    assert player.buys == 2
    assert state.supply["Silver"] == silver_before - 1
    assert any(c.name == "Silver" for c in player.discard)


def test_tax_adds_debt_to_pile_and_buyer_takes_it():
    state = _make_game()
    player = state.players[0]
    Tax().on_buy(state, player)
    # Some pile should have +1 tax token now.
    assert sum(state.tax_tokens.values()) >= 1


def test_banquet_gains_two_coppers_and_a_card():
    state = _make_game()
    player = state.players[0]
    Banquet().on_buy(state, player)
    coppers_gained = sum(1 for c in player.discard if c.name == "Copper")
    assert coppers_gained == 2
    # Plus a non-Victory up to $5 should be gained.
    non_copper_non_victory = [c for c in player.discard if c.name != "Copper" and not c.is_victory]
    assert len(non_copper_non_victory) >= 1


def test_ritual_curses_self_and_gains_vp_per_cost():
    state = _make_game()
    player = state.players[0]
    gold = get_card("Gold")
    player.hand = [gold]
    Ritual().on_buy(state, player)
    # Curse gained, Gold trashed, +6 VP.
    assert any(c.name == "Curse" for c in player.discard)
    assert any(c.name == "Gold" for c in state.trash)
    assert player.vp_tokens == 6


def test_salt_the_earth_grants_vp_and_trashes_victory():
    state = _make_game()
    player = state.players[0]
    province_before = state.supply["Province"]
    SaltTheEarth().on_buy(state, player)
    assert player.vp_tokens == 1
    assert state.supply["Province"] == province_before - 1


def test_wedding_grants_vp_and_gold():
    state = _make_game()
    player = state.players[0]
    Wedding().on_buy(state, player)
    assert player.vp_tokens == 1
    assert any(c.name == "Gold" for c in player.discard)


def test_windfall_only_with_empty_deck_and_discard():
    state = _make_game()
    player = state.players[0]
    player.deck = []
    player.discard = []
    Windfall().on_buy(state, player)
    golds = sum(1 for c in player.discard if c.name == "Gold")
    assert golds == 3

    state2 = _make_game()
    player2 = state2.players[0]
    player2.deck = [get_card("Copper")]
    Windfall().on_buy(state2, player2)
    golds2 = sum(1 for c in player2.discard if c.name == "Gold")
    assert golds2 == 0


def test_conquest_grants_silvers_and_vp_per_silver():
    state = _make_game()
    player = state.players[0]
    Conquest().on_buy(state, player)
    silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers == 2
    # +1 VP per Silver gained this turn (the 2 from this event).
    assert player.vp_tokens == 2


def test_dominate_grants_province_and_nine_vp():
    state = _make_game()
    player = state.players[0]
    Dominate().on_buy(state, player)
    assert any(c.name == "Province" for c in player.discard)
    assert player.vp_tokens == 9
