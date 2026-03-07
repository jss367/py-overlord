"""Tests for the Gatekeeper attack exile-on-gain mechanic."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


def _setup_two_players():
    """Create a two-player game with Gatekeeper in the supply."""
    ai1 = DummyAI()
    ai2 = DummyAI()
    p1 = PlayerState(ai1)
    p2 = PlayerState(ai2)
    state = GameState([p1, p2])
    state.supply = {
        "Gatekeeper": 10,
        "Village": 10,
        "Silver": 40,
        "Gold": 30,
        "Estate": 8,
        "Copper": 46,
    }
    return state, p1, p2


def test_gatekeeper_exiles_gained_action():
    """Opponent gains an Action while under Gatekeeper attack → card exiled."""
    state, p1, p2 = _setup_two_players()
    p2.gatekeeper_attacks = 1

    village = get_card("Village")
    state.supply["Village"] -= 1
    state.gain_card(p2, village)

    assert any(c.name == "Village" for c in p2.exile)
    assert all(c.name != "Village" for c in p2.discard)


def test_gatekeeper_exiles_gained_treasure():
    """Opponent gains a Treasure while under Gatekeeper attack → card exiled."""
    state, p1, p2 = _setup_two_players()
    p2.gatekeeper_attacks = 1

    silver = get_card("Silver")
    state.supply["Silver"] -= 1
    state.gain_card(p2, silver)

    assert any(c.name == "Silver" for c in p2.exile)
    assert all(c.name != "Silver" for c in p2.discard)


def test_gatekeeper_skips_victory_cards():
    """Opponent gains a Victory card → normal gain, not exiled."""
    state, p1, p2 = _setup_two_players()
    p2.gatekeeper_attacks = 1

    estate = get_card("Estate")
    state.supply["Estate"] -= 1
    state.gain_card(p2, estate)

    assert any(c.name == "Estate" for c in p2.discard)
    assert all(c.name != "Estate" for c in p2.exile)


def test_gatekeeper_skips_if_already_in_exile():
    """If opponent already has a copy in exile, card is gained normally."""
    state, p1, p2 = _setup_two_players()
    p2.gatekeeper_attacks = 1
    p2.exile = [get_card("Village")]  # Already have one in exile

    village = get_card("Village")
    state.supply["Village"] -= 1
    state.gain_card(p2, village)

    # gain_card reclaims from exile, so exile should be empty now
    # and discard should have the reclaimed card
    assert any(c.name == "Village" for c in p2.discard)


def test_gatekeeper_wears_off_after_duration():
    """After Gatekeeper's duration resolves, gains are normal."""
    state, p1, p2 = _setup_two_players()
    p2.gatekeeper_attacks = 1

    # Simulate duration resolving
    gatekeeper = get_card("Gatekeeper")
    p2.gatekeeper_attacks = max(0, p2.gatekeeper_attacks - 1)

    village = get_card("Village")
    state.supply["Village"] -= 1
    state.gain_card(p2, village)

    assert any(c.name == "Village" for c in p2.discard)
    assert all(c.name != "Village" for c in p2.exile)
