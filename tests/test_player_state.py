from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


def test_initialize_no_shelters():
    player = PlayerState(DummyAI())
    player.initialize(use_shelters=False)

    # Total starting cards should be 10 (7 Copper + 3 Estate)
    total_cards = len(player.hand) + len(player.deck) + len(player.discard)
    assert total_cards == 10
    assert player.count_in_deck("Copper") == 7
    assert player.count_in_deck("Estate") == 3

    # Player starts with 5 cards in hand and base resources
    assert len(player.hand) == 5
    assert player.actions == 1
    assert player.buys == 1


def test_initialize_with_shelters():
    player = PlayerState(DummyAI())
    player.initialize(use_shelters=True)

    total_cards = len(player.hand) + len(player.deck) + len(player.discard)
    assert total_cards == 10
    assert player.count_in_deck("Copper") == 7
    assert player.count_in_deck("Necropolis") == 1
    assert player.count_in_deck("Hovel") == 1
    assert player.count_in_deck("Overgrown Estate") == 1
    assert len(player.hand) == 5
