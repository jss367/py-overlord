"""Tests for the Guilds Overpay mechanic + the four affected cards.

Covers:
- Buying Masterpiece with overpay actually gains Silvers.
- Buying Stonemason with overpay gains 2 Action cards each costing exactly N.
- Buying Doctor with overpay peeks the top of deck and trashes/discards/topdecks.
- Buying Herald with overpay topdecks cards from the discard pile.
- Buying without overpay still works (overpay defaults 0).
- Cards that don't support overpay never trigger the AI hook.
- Overpay capped at available coins.
- Overpay never fires on plain gain (only on buy).
"""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class OverpayingAI(DummyAI):
    """AI that records overpay decisions and applies a configurable amount."""

    def __init__(
        self,
        overpay: int = 0,
        doctor_action: str = "trash",
        target_card: str = "",
    ):
        super().__init__()
        self.overpay_amount_to_use = overpay
        self.doctor_action = doctor_action
        self.target_card = target_card
        self.overpay_calls: list[tuple] = []

    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None and c.name == self.target_card:
                return c
        return None

    def choose_overpay_amount(self, state, player, card, max_amount):
        self.overpay_calls.append((card.name, max_amount))
        return min(self.overpay_amount_to_use, max_amount)

    def choose_doctor_overpay_action(self, state, player, card):
        return self.doctor_action

    def choose_herald_overpay_topdeck(self, state, player, choices):
        return choices[0] if choices else None


def _make_state(ai=None):
    ai = ai or OverpayingAI()
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.duration = []
    player.actions = 0
    player.buys = 1
    player.coins = 0
    player.coin_tokens = 0
    state.current_player_index = 0
    state.phase = "buy"
    return state, player


# --- Base hooks -------------------------------------------------------------


def test_default_card_does_not_allow_overpay():
    """Plain cards should not allow overpay; the AI hook isn't called."""

    ai = OverpayingAI(overpay=5, target_card="Silver")
    state, player = _make_state(ai)
    player.coins = 10

    state.handle_buy_phase()

    assert ai.overpay_calls == [], (
        f"overpay hook should not fire on Silver, got {ai.overpay_calls}"
    )
    assert any(c.name == "Silver" for c in player.discard)


# --- Masterpiece ------------------------------------------------------------


def test_masterpiece_overpay_three_gains_three_silvers():
    """Buying Masterpiece with $3 overpay gains exactly 3 Silvers in discard."""

    ai = OverpayingAI(overpay=3, target_card="Masterpiece")
    state, player = _make_state(ai)
    state.supply["Masterpiece"] = 10
    player.coins = 6  # cost $3 + overpay $3

    state.handle_buy_phase()

    silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers == 3, f"expected 3 Silvers from $3 overpay, got {silvers}"
    assert any(c.name == "Masterpiece" for c in player.discard)
    assert player.coins == 0


def test_masterpiece_no_overpay_gains_only_the_card():
    ai = OverpayingAI(overpay=0, target_card="Masterpiece")
    state, player = _make_state(ai)
    state.supply["Masterpiece"] = 10
    player.coins = 3

    state.handle_buy_phase()

    assert sum(1 for c in player.discard if c.name == "Silver") == 0
    assert any(c.name == "Masterpiece" for c in player.discard)


def test_masterpiece_overpay_calls_ai_with_correct_max():
    """Overpay max should be the player's coins remaining after the printed cost."""
    ai = OverpayingAI(overpay=2, target_card="Masterpiece")
    state, player = _make_state(ai)
    state.supply["Masterpiece"] = 10
    player.coins = 7  # cost $3, leaves $4 max overpay

    state.handle_buy_phase()

    assert ai.overpay_calls == [("Masterpiece", 4)]


# --- Stonemason -------------------------------------------------------------


def test_stonemason_overpay_gains_two_actions_at_exact_cost():
    """Buying Stonemason with $4 overpay gains 2 Action cards each cost $4."""

    ai = OverpayingAI(overpay=4, target_card="Stonemason")
    state, player = _make_state(ai)
    state.supply["Stonemason"] = 10
    state.supply["Smithy"] = 10  # Action, costs $4
    player.coins = 6  # cost $2 + overpay $4

    state.handle_buy_phase()

    smithies = sum(1 for c in player.discard if c.name == "Smithy")
    assert smithies == 2, f"expected 2 Smithies (cost $4 Actions), got {smithies}"
    assert any(c.name == "Stonemason" for c in player.discard)


def test_stonemason_no_overpay_does_not_gain_extras():
    ai = OverpayingAI(overpay=0, target_card="Stonemason")
    state, player = _make_state(ai)
    state.supply["Stonemason"] = 10
    state.supply["Smithy"] = 10
    player.coins = 2

    state.handle_buy_phase()
    assert sum(1 for c in player.discard if c.name == "Smithy") == 0
    assert any(c.name == "Stonemason" for c in player.discard)


def test_stonemason_overpay_with_no_matching_actions_gains_nothing_extra():
    """If no Action card costs exactly $N, overpay still goes through."""
    ai = OverpayingAI(overpay=7, target_card="Stonemason")
    state, player = _make_state(ai)
    state.supply["Stonemason"] = 10
    # No Action cards in the kingdom — only basic cards which are mostly
    # Treasures / Victory. There's no $7 Action available.
    player.coins = 9

    state.handle_buy_phase()
    # Stonemason still bought, no extra Action gains, coins fully spent.
    assert any(c.name == "Stonemason" for c in player.discard)
    assert player.coins == 0


# --- Doctor -----------------------------------------------------------------


def test_doctor_overpay_one_trashes_top_card_when_ai_picks_trash():
    ai = OverpayingAI(overpay=1, doctor_action="trash", target_card="Doctor")
    state, player = _make_state(ai)
    state.supply["Doctor"] = 10

    junk = get_card("Curse")
    player.deck = [junk]
    player.coins = 4

    state.handle_buy_phase()

    assert junk in state.trash
    assert junk not in player.deck
    assert junk not in player.discard


def test_doctor_overpay_topdeck_keeps_card_on_deck():
    ai = OverpayingAI(overpay=1, doctor_action="topdeck", target_card="Doctor")
    state, player = _make_state(ai)
    state.supply["Doctor"] = 10

    gold = get_card("Gold")
    player.deck = [gold]
    player.coins = 4

    state.handle_buy_phase()

    assert gold in player.deck
    assert gold not in state.trash
    assert gold not in player.discard


def test_doctor_overpay_discard_moves_to_discard():
    ai = OverpayingAI(overpay=1, doctor_action="discard", target_card="Doctor")
    state, player = _make_state(ai)
    state.supply["Doctor"] = 10

    estate = get_card("Estate")
    player.deck = [estate]
    player.coins = 4

    state.handle_buy_phase()
    assert estate in player.discard
    assert estate not in player.deck
    assert estate not in state.trash


# --- Herald -----------------------------------------------------------------


def test_herald_overpay_two_topdecks_two_cards_from_discard():
    ai = OverpayingAI(overpay=2, target_card="Herald")
    state, player = _make_state(ai)
    state.supply["Herald"] = 10

    smithy = get_card("Smithy")
    village = get_card("Village")
    player.discard = [smithy, village]
    player.coins = 6

    state.handle_buy_phase()

    assert smithy in player.deck
    assert village in player.deck
    assert smithy not in player.discard
    assert village not in player.discard


def test_herald_overpay_zero_does_nothing_to_discard():
    ai = OverpayingAI(overpay=0, target_card="Herald")
    state, player = _make_state(ai)
    state.supply["Herald"] = 10

    smithy = get_card("Smithy")
    player.discard = [smithy]
    player.coins = 4

    state.handle_buy_phase()
    assert smithy in player.discard
    assert smithy not in player.deck


# --- Buy hook safety --------------------------------------------------------


def test_overpay_capped_at_available_coins():
    """Even if AI returns a huge number, overpay cannot exceed available coins."""

    class GreedyOverpay(OverpayingAI):
        def choose_overpay_amount(self, state, player, card, max_amount):
            self.overpay_calls.append((card.name, max_amount))
            return 999

    ai = GreedyOverpay(target_card="Masterpiece")
    state, player = _make_state(ai)
    state.supply["Masterpiece"] = 10
    player.coins = 5  # cost $3, leaves $2

    state.handle_buy_phase()

    silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers == 2, f"expected 2 Silvers (capped overpay), got {silvers}"
    assert player.coins == 0


def test_overpay_does_not_fire_on_gain_only_on_buy():
    """Direct gain_card (not via buy) should never trigger overpay."""
    ai = OverpayingAI(overpay=3, target_card="Masterpiece")
    state, player = _make_state(ai)
    state.supply["Masterpiece"] = 10
    player.coins = 999

    state.gain_card(player, get_card("Masterpiece"))

    assert ai.overpay_calls == []
    assert sum(1 for c in player.discard if c.name == "Silver") == 0


# --- Coin tokens as spendable overpay currency -----------------------------


def test_overpay_can_be_paid_with_coin_tokens():
    """Coin tokens should be spendable for overpay just like coins."""

    ai = OverpayingAI(overpay=2, target_card="Masterpiece")
    state, player = _make_state(ai)
    state.supply["Masterpiece"] = 10
    # Cost $3 — pay with all coins, leaving only coin tokens for overpay.
    player.coins = 3
    player.coin_tokens = 5

    state.handle_buy_phase()

    silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers == 2, f"expected 2 Silvers from $2 token-overpay, got {silvers}"
    # 2 of the 5 coin tokens were spent on overpay.
    assert player.coin_tokens == 3
    assert player.coins == 0


def test_overpay_max_amount_includes_coin_tokens():
    """The AI's max_amount should include both coins and coin tokens."""

    ai = OverpayingAI(overpay=0, target_card="Masterpiece")
    state, player = _make_state(ai)
    state.supply["Masterpiece"] = 10
    player.coins = 3  # exactly cost
    player.coin_tokens = 4

    state.handle_buy_phase()

    # max_amount should be 0 (coins) + 4 (tokens) = 4.
    assert ai.overpay_calls == [("Masterpiece", 4)]


# --- Black Market: overpay must trigger via that buy path too --------------


def test_black_market_buying_masterpiece_triggers_overpay():
    """Buying Masterpiece via Black Market should fire overpay (not just buy phase)."""
    from dominion.cards.promo.black_market import BlackMarket

    ai = OverpayingAI(overpay=3, target_card="Masterpiece")
    state, player = _make_state(ai)
    state.supply["Masterpiece"] = 10

    # Force Black Market to reveal Masterpiece.
    state.black_market_deck = ["Masterpiece"]

    # AI must agree to buy revealed Masterpiece.
    def _choose_bm(state, player, choices):
        for c in choices:
            if c.name == "Masterpiece":
                return c
        return None

    ai.choose_black_market_purchase = _choose_bm  # type: ignore[assignment]
    ai.order_cards_for_black_market_bottom = (  # type: ignore[assignment]
        lambda state, player, choices: list(choices)
    )

    player.coins = 6  # cost $3 + overpay $3
    player.buys = 1

    BlackMarket().play_effect(state)

    silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers == 3, f"Black Market overpay should gain 3 Silvers, got {silvers}"
    assert any(c.name == "Masterpiece" for c in player.discard)
    assert ai.overpay_calls and ai.overpay_calls[-1][0] == "Masterpiece"
