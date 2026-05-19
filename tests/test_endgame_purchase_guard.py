"""Engine-level guard: never make a buy that ends the game while losing.

The strategy layer chooses *what* it wants to buy; these tests pin the
engine behaviour that vetoes a buy when committing it would trigger the
game-end condition (last Province/Colony, or the third empty pile) and
the buying player would not be ahead.
"""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class PriorityBuyAI(DummyAI):
    """Buys the first card (by name priority) present in the offered choices."""

    def __init__(self, priority):
        super().__init__()
        self.priority = list(priority)

    def choose_buy(self, state, choices):
        available = {c.name: c for c in choices if c is not None}
        for name in self.priority:
            if name in available:
                return available[name]
        return None


def make_state(current_ai, opponent_deck):
    me = PlayerState(current_ai)
    opponent = PlayerState(DummyAI())
    opponent.hand = []
    opponent.deck = list(opponent_deck)
    opponent.discard = []
    state = GameState([me, opponent])
    state.log_callback = lambda *_: None
    me.hand = []
    me.deck = []
    me.discard = []
    me.actions = 0
    return state, me, opponent


def test_does_not_buy_last_province_when_behind():
    """Buying the last Province ends the game; if it leaves us behind,
    the engine must veto it and let the strategy take its next choice."""
    ai = PriorityBuyAI(["Province", "Gold"])
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")] * 5)
    state.supply = {"Province": 1, "Gold": 10, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Province"] == 1  # last Province NOT taken
    assert state.supply["Gold"] == 9  # next-best bought instead
    assert "Province" not in me.bought_this_turn
    assert "Gold" in me.bought_this_turn


def test_buys_last_province_when_ahead():
    """If taking the last Province ends the game while we are ahead, the
    engine must not interfere."""
    ai = PriorityBuyAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=[])
    me.deck = [get_card("Province")] * 5  # 30 VP, miles ahead
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Province"] == 0
    assert "Province" in me.bought_this_turn


def test_does_not_trigger_third_pile_out_when_behind():
    """The third empty pile also ends the game; the guard must cover it,
    not just Province/Colony depletion."""
    ai = PriorityBuyAI(["Market", "Copper"])
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")] * 3)
    # Two kingdom piles already empty; buying Market would empty a third.
    state.supply = {
        "Village": 0,
        "Smithy": 0,
        "Market": 1,
        "Copper": 30,
        "Province": 8,
    }
    me.coins = 5
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Market"] == 1  # third pile-out vetoed
    assert state.supply["Copper"] == 29  # next-best bought instead
    assert "Market" not in me.bought_this_turn


def test_allow_losing_pileout_override_disables_guard():
    """A strategy can opt out of the guard via allow_losing_pileout."""
    ai = PriorityBuyAI(["Province"])
    ai.allow_losing_pileout = True
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")] * 5)
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Province"] == 0  # guard disabled, buy went through
    assert "Province" in me.bought_this_turn


def test_guard_does_not_block_non_game_ending_buy_when_behind():
    """Being behind is irrelevant when the buy does not end the game."""
    ai = PriorityBuyAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")] * 5)
    state.supply = {"Province": 8, "Copper": 30}  # plenty left
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Province"] == 7
    assert "Province" in me.bought_this_turn


def test_guard_skipped_when_goons_would_swing_the_score():
    """Goons grants +VP per buy at buy time, which the cheap simulation
    does not model. With Goons played, the buyer's real end score can be
    higher than the card-only estimate, so the guard must not veto the
    last Province on a card-VP tie/deficit."""
    ai = PriorityBuyAI(["Province"])
    # Opponent on 6; buyer reaches only 6 by card VP alone (a "losing"
    # tie under the guard), but two Goons played add +2 → real win.
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")])
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1
    me.goons_played = 2

    state.handle_buy_phase()

    assert state.supply["Province"] == 0  # winning buy not vetoed
    assert "Province" in me.bought_this_turn


def test_guard_skipped_when_vp_awarding_landmark_in_play():
    """Landmarks like Battlefield award VP via on_gain/on_buy during the
    real buy path; the cheap simulation ignores them, so the guard must
    not veto endgame buys on boards carrying such a landmark."""
    from dominion.landmarks.landmarks import Battlefield

    ai = PriorityBuyAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")] * 4)
    state.landmarks = [Battlefield()]
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Province"] == 0  # guard stands down on VP-hook boards
    assert "Province" in me.bought_this_turn
