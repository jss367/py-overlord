from dominion.cards.registry import get_card
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


    
def test_vp_breakdown_initial_deck():
    player = PlayerState(DummyAI())
    player.initialize(use_shelters=False)
    breakdown = player.get_vp_breakdown()
    assert breakdown["Estate"]["count"] == 3
    assert breakdown["Estate"]["vp"] == 3

    
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


def test_all_cards_includes_additional_zones():
    player = PlayerState(DummyAI())

    estate = get_card("Estate")
    province = get_card("Province")
    duchy_one = get_card("Duchy")
    duchy_two = get_card("Duchy")
    copper = get_card("Copper")

    player.exile.append(estate)
    player.invested_exile.append(estate)
    player.native_village_mat.append(copper)
    player.trickster_set_aside.append(province)
    player.delayed_cards.append(duchy_one)
    player.flagship_pending.append(duchy_two)

    assert player.count_in_deck("Estate") == 1
    assert player.count_in_deck("Copper") == 1
    assert player.count_in_deck("Province") == 1
    assert player.count_in_deck("Duchy") == 2
    assert player.get_victory_points(None) == 13
