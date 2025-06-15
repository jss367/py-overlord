from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.cards.registry import get_card
from tests.utils import DummyAI


def test_bridge_cost_reduction_affordable():
    player = PlayerState(DummyAI())
    state = GameState([player], supply={"Smithy": 1})
    player.coins = 3

    affordable = state._get_affordable_cards(player)
    assert not any(card.name == "Smithy" for card in affordable)

    player.cost_reduction = 1
    affordable = state._get_affordable_cards(player)
    assert any(card.name == "Smithy" for card in affordable)


def test_bridge_purchase_cost_reduced():
    player = PlayerState(DummyAI())
    state = GameState([player], supply={"Smithy": 1})
    player.coins = 3
    player.buys = 1
    player.cost_reduction = 1

    smithy = get_card("Smithy")
    state._complete_purchase(player, smithy)
    assert player.coins == 0
    assert state.supply["Smithy"] == 0

