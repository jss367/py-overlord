"""Regression tests for ordered-pile (Knights, Ruins) restoration through
the Trader and Exile-reclamation paths in ``GameState.gain_card``.

Both restoration paths historically used ``card.name`` to bump the supply
count, which silently no-ops for ordered piles whose supply key is the
pile placeholder (``"Knights"``, ``"Ruins"``) rather than the specific
top card's name (e.g. ``"Sir Bailey"``). This let supply leak and
``pile_order`` desynchronise from ``supply``.
"""

from typing import Optional, Set

from dominion.cards.dark_ages.knights import KNIGHT_NAMES
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState

from tests.utils import DummyAI


class _RevealTraderAI(DummyAI):
    def __init__(self, reveal_for: Set[str]) -> None:
        super().__init__()
        self.reveal_for = reveal_for

    def should_reveal_trader(self, state, player, gained_card, *, to_deck) -> bool:
        return gained_card.name in self.reveal_for


def _prepare_state_with_knights(ai) -> tuple[GameState, "PlayerState", str]:
    """Initialise a game with the Knights pile present and return the state,
    the (only) player, and the name of the current top-of-pile Knight."""

    state = GameState(players=[])
    state.initialize_game(
        [ai],
        [get_card("Knights"), get_card("Trader")],
    )
    player = state.players[0]
    player.actions = 1
    player.hand = []
    player.discard = []
    player.deck = []
    player.in_play = []
    top_name = state.pile_order["Knights"][-1]
    return state, player, top_name


def test_trader_restores_ordered_knights_pile():
    """When Trader replaces a Knight gain with Silver, the Knights pile
    placeholder count and pile_order must both be restored."""

    ai = _RevealTraderAI(reveal_for=set(KNIGHT_NAMES))
    state, player, top_name = _prepare_state_with_knights(ai)
    player.hand = [get_card("Trader")]
    state.supply["Silver"] = 40

    knights_before = state.supply["Knights"]
    order_len_before = len(state.pile_order["Knights"])

    # Caller decrements supply + pops pile_order before calling gain_card,
    # mirroring how University / Displace gain from an ordered pile.
    state.supply["Knights"] -= 1
    state.pile_order["Knights"].pop()
    gained = state.gain_card(player, get_card(top_name))

    assert gained.name == "Silver", "Trader should have swapped to Silver"
    # The Knights pile must be fully restored — supply count AND pile_order.
    assert state.supply["Knights"] == knights_before
    assert len(state.pile_order["Knights"]) == order_len_before
    assert state.pile_order["Knights"][-1] == top_name


def test_exile_reclaim_restores_ordered_knights_pile():
    """When a gain is reclaimed from the Exile mat, the Supply pile that
    was decremented for the gain must be restored. For ordered piles this
    means the placeholder key and pile_order, not the card-specific name."""

    state, player, top_name = _prepare_state_with_knights(DummyAI())
    # Put a matching Knight on the Exile mat so the next gain is reclaimed.
    exiled = get_card(top_name)
    player.exile.append(exiled)

    knights_before = state.supply["Knights"]
    order_len_before = len(state.pile_order["Knights"])

    state.supply["Knights"] -= 1
    state.pile_order["Knights"].pop()
    gained = state.gain_card(player, get_card(top_name))

    assert gained is exiled, "Exile mat copy should be reclaimed"
    assert state.supply["Knights"] == knights_before
    assert len(state.pile_order["Knights"]) == order_len_before
    assert state.pile_order["Knights"][-1] == top_name
