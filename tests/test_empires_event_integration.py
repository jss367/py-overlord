"""Integration tests for Empires events that touch game state hooks."""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI, BuyEventAI


def _make_game(events, num_players=2):
    players = [PlayerState(BuyEventAI()) for _ in range(num_players)]
    state = GameState(players=players)
    state.log_callback = lambda *a, **k: None
    state.initialize_game(
        [BuyEventAI() for _ in range(num_players)],
        [get_card("Village")],
        events=events,
    )
    return state


def test_donate_resolves_at_end_of_buy_phase():
    state = _make_game([get_event("Donate")])
    player = state.players[0]
    player.coins = 0
    player.buys = 1

    # Manually trigger donate buy + buy phase end
    get_event("Donate").on_buy(state, player)
    assert player.donate_pending == 1

    # Run buy phase end resolution
    state._handle_buy_phase_end(player)
    # Donate should be resolved.
    assert player.donate_pending == 0
    # Player should have 5 cards in hand now.
    assert len(player.hand) == 5


def test_tax_setup_places_one_debt_per_pile():
    state = _make_game([get_event("Tax")])
    # All supply piles should have 1 tax debt token.
    for pile_name in state.supply:
        assert state.tax_tokens.get(pile_name, 0) == 1, pile_name


def test_tax_buyer_pays_extra_debt():
    state = _make_game([get_event("Tax")])
    player = state.players[0]
    # Spend Tax setup debt manually to verify _apply_tax_tokens semantics.
    state.tax_tokens["Silver"] = 3
    debt_before = player.debt
    state._apply_tax_tokens(player, "Silver")
    assert player.debt == debt_before + 3
    assert state.tax_tokens["Silver"] == 0
