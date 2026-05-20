"""Direct coverage for the shared single-buy commit helper."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def test_commit_buy_decrements_supply_and_records_buy():
    player = PlayerState(DummyAI())
    state = GameState([player])
    state.log_callback = lambda *_: None
    state.supply = {"Silver": 10, "Copper": 30}
    player.coins = 3
    player.buys = 1

    state._commit_buy(player, get_card("Silver"))

    assert state.supply["Silver"] == 9
    assert "Silver" in player.bought_this_turn
    assert player.coins == 0
    assert any(card.name == "Silver" for card in player.discard)
