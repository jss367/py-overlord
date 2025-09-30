from dominion.cards.registry import get_card
from dominion.game.player_state import PlayerState
from dominion.game.game_state import GameState
from tests.utils import DummyAI


def play_action(state, player, card):
    player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


def test_inventor_gains_reduced_cost_card_and_adds_discount():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([])

    # Only keep the piles we care about for this test
    state.supply = {"Laboratory": 10}

    inventor = get_card("Inventor")
    player.hand = [inventor]
    player.actions = 1
    player.cost_reduction = 1

    play_action(state, player, inventor)

    assert any(card.name == "Laboratory" for card in player.discard)
    assert state.supply["Laboratory"] == 9
    assert player.cost_reduction == 2


def test_inventor_handles_no_affordable_cards_but_still_reduces_cost():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([])

    # Provide only an unaffordable pile
    state.supply = {"Laboratory": 10}

    inventor = get_card("Inventor")
    player.hand = [inventor]
    player.actions = 1

    play_action(state, player, inventor)

    assert not player.discard
    assert state.supply["Laboratory"] == 10
    assert player.cost_reduction == 1
