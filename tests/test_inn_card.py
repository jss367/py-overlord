from dominion.cards.registry import get_card
from dominion.game.player_state import PlayerState
from dominion.game.game_state import GameState
from tests.utils import DummyAI


def play_action(state, player, card):
    player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


def test_inn_draws_two_and_discards_two_preserving_the_rest_of_hand():
    player = PlayerState(DummyAI())
    state = GameState([player])
    state.setup_supply([])
    inn = get_card("Inn")
    player.hand = [inn, get_card("Copper"), get_card("Estate"), get_card("Gold")]
    player.deck = [get_card("Silver"), get_card("Village"), get_card("Smithy")]
    play_action(state, player, inn)
    assert [c.name for c in player.discard] == ["Estate", "Copper"]
    assert sorted(c.name for c in player.hand) == ["Gold", "Smithy", "Village"]
    assert [c.name for c in player.deck] == ["Silver"]
    assert inn in player.in_play
