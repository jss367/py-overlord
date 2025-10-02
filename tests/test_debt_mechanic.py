from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class BuyOverlordThenSilverAI(DummyAI):
    """AI that prioritises buying Overlord, then Silver."""

    def choose_buy(self, state, choices):
        for choice in choices:
            if choice is None:
                continue
            if (
                choice.name == "Overlord"
                and "Overlord" not in state.current_player.bought_this_turn
            ):
                return choice
        for choice in choices:
            if choice is None:
                continue
            if choice.name == "Silver":
                return choice
        return None


def make_state(ai=None):
    player = PlayerState(ai or DummyAI())
    state = GameState([player])
    state.log_callback = lambda *_: None
    return state, player


def test_capital_adds_debt_on_cleanup():
    state, player = make_state()
    capital = get_card("Capital")
    player.in_play = [capital]
    player.hand = []
    player.deck = []
    player.discard = []

    state.handle_cleanup_phase()

    assert player.debt == 6
    total_capitals = sum(
        1 for zone in (player.hand, player.deck, player.discard) for card in zone if card.name == "Capital"
    )
    assert total_capitals == 1


def test_buying_debt_card_requires_payment_before_second_purchase():
    state, player = make_state(BuyOverlordThenSilverAI())
    state.supply = {"Overlord": 10, "Silver": 10}
    player.coins = 11
    player.buys = 2

    state.handle_buy_phase()

    assert player.debt == 0
    assert player.coins == 0
    assert player.coins_spent_this_turn == 11
    assert state.supply["Overlord"] == 9
    assert state.supply["Silver"] == 9


def test_buying_debt_card_leaves_outstanding_debt_when_unpaid():
    state, player = make_state(BuyOverlordThenSilverAI())
    state.supply = {"Overlord": 10}
    player.coins = 0
    player.buys = 1

    state.handle_buy_phase()

    assert player.debt == 8
    assert state.supply["Overlord"] == 9
    assert player.buys == 0


def test_players_can_pay_debt_without_buys():
    state, player = make_state()
    player.debt = 4
    player.coins = 3
    player.buys = 0

    state.handle_buy_phase()

    assert player.debt == 1
    assert player.coins == 0
    assert player.coins_spent_this_turn == 3
