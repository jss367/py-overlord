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


def provinces(n):
    """``n`` *distinct* Province cards.

    ``PlayerState.all_cards()`` dedups by ``id``, so ``[get_card("X")] * n``
    (one aliased object) under-counts a deck's victory points. Tests must
    build distinct instances to model a genuinely ahead/behind opponent.
    """
    return [get_card("Province") for _ in range(n)]


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
    state, me, _opp = make_state(ai, opponent_deck=provinces(5))
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
    me.deck = provinces(5)  # 30 VP, miles ahead
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
    state, me, _opp = make_state(ai, opponent_deck=provinces(3))
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
    state, me, _opp = make_state(ai, opponent_deck=provinces(5))
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Province"] == 0  # guard disabled, buy went through
    assert "Province" in me.bought_this_turn


def test_guard_does_not_block_non_game_ending_buy_when_behind():
    """Being behind is irrelevant when the buy does not end the game."""
    ai = PriorityBuyAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=provinces(5))
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
    """Battlefield's real +VP gain can make the endgame buy safe."""
    from dominion.landmarks.landmarks import Battlefield

    ai = PriorityBuyAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")])
    state.landmarks = [Battlefield()]
    state.landmarks[0].setup(state)
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Province"] == 0
    assert "Province" in me.bought_this_turn


def test_guard_skipped_when_groundskeeper_would_swing_the_score():
    """Groundskeeper grants +VP per Victory card gained while in play
    (game_state.py:3417). The cheap simulation does not model it, so the
    guard must not veto the last Province on a card-VP tie/deficit."""
    ai = PriorityBuyAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")])
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1
    me.groundskeeper_bonus = 2  # +2 VP on the Province gain → real win

    state.handle_buy_phase()

    assert state.supply["Province"] == 0  # winning buy not vetoed
    assert "Province" in me.bought_this_turn


def test_guard_skipped_when_collection_would_swing_the_score():
    """Collection grants +VP per Action card gained while in play
    (base_card.py:278). Buying the Action that empties the third pile
    must not be vetoed when Collection would carry the buyer ahead."""
    ai = PriorityBuyAI(["Market", "Copper"])
    state, me, _opp = make_state(ai, opponent_deck=[])
    state.supply = {
        "Village": 0,
        "Smithy": 0,
        "Market": 1,
        "Copper": 30,
        "Province": 8,
    }
    me.coins = 5
    me.buys = 1
    me.collection_played = 1  # +VP on the Market (Action) gain

    state.handle_buy_phase()

    assert state.supply["Market"] == 0  # winning pile-out not vetoed
    assert "Market" in me.bought_this_turn


def test_guard_skipped_when_exiled_copy_reclaimed():
    """With a matching card on the Exile mat the real buy reclaims it and
    restores the supply (game_state.py:3401), so the pile is not actually
    depleted and the game does not end — the guard must not veto."""
    ai = PriorityBuyAI(["Province"])
    # Distinct objects: all_cards() dedups by id, so aliased copies would
    # under-count the opponent and make the buyer look ahead.
    state, me, _opp = make_state(
        ai, opponent_deck=provinces(3)
    )
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1
    me.exile = [get_card("Province")]  # reclaimed instead of depleting

    state.handle_buy_phase()

    assert state.supply["Province"] == 1  # pile restored, game did not end
    assert "Province" in me.bought_this_turn


class _RevealsTraderAI(PriorityBuyAI):
    def should_reveal_trader(self, state, player, gained_card, *, to_deck):
        return True


def test_guard_skipped_when_trader_can_restore_pile():
    """Trader can exchange the real gain, so the Province pile is restored."""
    ai = _RevealsTraderAI(["Province"])
    state, me, _opp = make_state(
        ai, opponent_deck=provinces(4)
    )
    state.supply = {"Province": 1, "Silver": 10, "Copper": 30}
    me.coins = 8
    me.buys = 1
    me.hand = [get_card("Trader")]

    state.handle_buy_phase()

    assert "Province" in me.bought_this_turn
    assert state.supply["Province"] == 1
    assert state.supply["Silver"] == 9


class _ExchangesChangelingAI(PriorityBuyAI):
    def should_exchange_changeling(self, state, player, gained_card):
        return True


def test_guard_skipped_when_changeling_pile_available():
    """Changeling can exchange the real gain, so the Province pile is restored."""
    ai = _ExchangesChangelingAI(["Province"])
    state, me, _opp = make_state(
        ai, opponent_deck=provinces(4)
    )
    state.supply = {"Province": 1, "Changeling": 10, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert "Province" in me.bought_this_turn
    assert state.supply["Province"] == 1
    assert state.supply["Changeling"] == 9


def test_false_negative_blocked_when_hoard_empties_third_pile():
    """Hoard can empty Gold during a Victory buy, ending the game by pile-out."""
    ai = PriorityBuyAI(["Province", "Copper"])
    state, me, _opp = make_state(ai, opponent_deck=provinces(4))
    state.supply = {
        "Province": 8,
        "Gold": 1,
        "Village": 0,
        "Smithy": 0,
        "Copper": 30,
    }
    me.coins = 8
    me.buys = 1
    me.in_play = [get_card("Hoard")]

    state.handle_buy_phase()

    assert "Province" not in me.bought_this_turn
    assert "Copper" in me.bought_this_turn


def test_guard_disabled_when_any_ai_marks_decision_hooks_impure():
    ai = PriorityBuyAI(["Province"])
    ai.decision_hooks_are_pure = False
    state, me, _opp = make_state(ai, opponent_deck=provinces(5))
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert "Province" in me.bought_this_turn


def test_gain_would_lose_game_preserves_rng_state():
    import random

    ai = PriorityBuyAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=provinces(5))
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    random.seed(12345)
    before = random.getstate()
    state.gain_would_lose_game(me, get_card("Province"))
    after = random.getstate()

    assert before == after


def test_temple_endgame_correctly_handled():
    ai = PriorityBuyAI(["Temple"])
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")])
    state.supply = {
        "Temple": 1,
        "Province": 8,
        "Village": 0,
        "Smithy": 0,
        "Copper": 30,
    }
    state.temple_pile_tokens = 3
    me.coins = 5
    me.buys = 1

    state.handle_buy_phase()

    assert "Temple" not in me.bought_this_turn
