"""Integration tests for Empires events that touch game state hooks."""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.projects.fleet import Fleet

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


def test_donate_pending_set_on_buy_not_consumed_in_buy_phase_end():
    state = _make_game([get_event("Donate")])
    player = state.players[0]
    player.coins = 0
    player.buys = 1

    get_event("Donate").on_buy(state, player)
    assert player.donate_pending == 1

    # Donate is deferred until cleanup completes. _handle_buy_phase_end
    # must NOT consume donate_pending or draw a hand prematurely.
    hand_before = len(player.hand)
    state._handle_buy_phase_end(player)
    assert player.donate_pending == 1
    assert len(player.hand) == hand_before


def test_donate_resolves_after_cleanup_draw():
    """Donate fires AFTER cleanup's discard-and-draw so the Donate-drawn
    hand survives into the next turn instead of being immediately discarded."""
    state = _make_game([get_event("Donate")])
    player = state.players[0]
    state.current_player_index = state.players.index(player)

    get_event("Donate").on_buy(state, player)
    assert player.donate_pending == 1

    # Stack the deck with plenty of cards so cleanup's draw-5 has cards to
    # pull before Donate redraws.
    player.deck = [get_card("Copper") for _ in range(20)]
    player.hand = [get_card("Copper") for _ in range(3)]
    player.in_play = []
    player.duration = []
    player.multiplied_durations = []

    state.handle_cleanup_phase()
    # Donate should now have been resolved exactly once.
    assert player.donate_pending == 0
    # Final hand size is 5 from the post-Donate draw.
    assert len(player.hand) == 5


def test_donate_drawn_hand_survives_to_next_turn():
    """Regression: After Donate resolves at end of cleanup, the freshly-drawn
    5-card Donate hand must NOT be discarded — it must survive into the next
    turn. This preserves the intent of PR #187 (which moved Donate after the
    cleanup discard-and-draw)."""
    state = _make_game([get_event("Donate")])
    player = state.players[0]
    state.current_player_index = state.players.index(player)

    # Buy Donate.
    get_event("Donate").on_buy(state, player)
    assert player.donate_pending == 1

    # Stack the deck with distinguishable cards: Estates BEFORE cleanup so
    # cleanup's draw-5 pulls them. After Donate, the 5-card hand should be
    # post-Donate Coppers (Estates were trashed if AI chose to). To keep the
    # test simple, just give the player 20 Coppers and verify the post-cleanup
    # hand survives the immediate next is_game_over check.
    player.deck = [get_card("Copper") for _ in range(20)]
    player.hand = [get_card("Copper") for _ in range(3)]
    player.in_play = []
    player.duration = []
    player.multiplied_durations = []

    state.handle_cleanup_phase()

    # Donate consumed.
    assert player.donate_pending == 0
    # Hand has 5 cards after Donate.
    assert len(player.hand) == 5
    hand_after_cleanup = list(player.hand)

    # Simulate the start of the next turn: handle_start_phase must not wipe
    # the Donate-drawn hand.
    state.current_player_index = state.players.index(player)
    state.phase = "start"
    state.handle_start_phase()

    # The Donate-drawn cards must still be in hand (start phase does not
    # discard them).
    for card in hand_after_cleanup:
        assert card in player.hand, "Donate-drawn hand was wiped before next turn"


def test_donate_resolves_on_game_end_turn_with_fleet():
    """Regression: When the buyer of Donate empties Provinces (or otherwise
    triggers game-end) on the same turn, and another player owns Fleet, the
    Fleet extra round must NOT start before this player's cleanup finishes.
    Otherwise their pending Donate is silently dropped."""
    state = _make_game([get_event("Donate")], num_players=2)
    buyer = state.players[0]
    fleet_owner = state.players[1]

    # Give Player 2 the Fleet project.
    fleet_owner.projects.append(Fleet())

    # Set the buyer as the current player and buy Donate during their buy
    # phase.
    state.current_player_index = state.players.index(buyer)
    state.phase = "buy"
    get_event("Donate").on_buy(state, buyer)
    assert buyer.donate_pending == 1

    # Trigger game-end conditions: empty Provinces.
    state.supply["Province"] = 0
    assert state.supply.get("Province", 0) == 0

    # Mid-turn (phase != "start"), is_game_over must NOT short-circuit into
    # the Fleet extra round. It must let the current player's remaining
    # phases run first.
    assert state.is_game_over() is False
    assert state.fleet_extra_round_active is False

    # Now run the rest of the buy phase end + night + cleanup. Cleanup must
    # consume donate_pending.
    state._handle_buy_phase_end(buyer)
    state.phase = "night"
    state.handle_night_phase()
    assert state.phase == "cleanup"

    # Stack the deck so cleanup's draw has cards to pull.
    buyer.deck = [get_card("Copper") for _ in range(20)]
    buyer.hand = [get_card("Copper") for _ in range(3)]
    buyer.in_play = []
    buyer.duration = []
    buyer.multiplied_durations = []

    state.handle_cleanup_phase()

    # Donate must have resolved on the buyer's turn — not been silently
    # dropped by Fleet redirecting to the Fleet owner's start phase.
    assert buyer.donate_pending == 0
    assert len(buyer.hand) == 5

    # After cleanup, phase is "start". Now is_game_over may legitimately
    # transition into the Fleet extra round.
    assert state.phase == "start"
    state.is_game_over()
    assert state.fleet_extra_round_active is True
    assert fleet_owner in state.fleet_extra_players


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
