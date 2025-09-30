from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


def setup_state():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Flagship"), get_card("Village")])
    player = state.players[0]
    return state, player


def test_flagship_replays_next_action_and_adds_coins():
    state, player = setup_state()

    flagship = get_card("Flagship")
    village = get_card("Village")
    player.hand = [flagship, village] + [get_card("Copper") for _ in range(3)]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.actions = 2

    state.phase = "action"
    state.handle_action_phase()

    assert player.coins == 2
    assert player.actions == 4
    assert not player.flagship_pending
    assert all(card.name != "Flagship" for card in player.duration)


def test_flagship_effect_persists_to_next_turn():
    state, player = setup_state()

    flagship = get_card("Flagship")
    player.hand = [flagship] + [get_card("Copper") for _ in range(4)]
    player.deck = [get_card("Copper") for _ in range(4)] + [get_card("Village")]
    player.discard = []
    player.actions = 1

    state.phase = "action"
    state.handle_action_phase()

    assert len(player.flagship_pending) == 1
    assert any(card.name == "Flagship" for card in player.duration)

    state.handle_treasure_phase()
    state.handle_buy_phase()
    state.handle_cleanup_phase()

    assert len(player.flagship_pending) == 1
    assert any(card.name == "Flagship" for card in player.duration)

    state.handle_start_phase()
    assert len(player.flagship_pending) == 1

    state.handle_action_phase()

    assert not player.flagship_pending
    assert all(card.name != "Flagship" for card in player.duration)
    assert player.actions == 4
