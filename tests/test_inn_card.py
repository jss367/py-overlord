from dominion.cards.registry import get_card
from dominion.game.player_state import PlayerState
from dominion.game.game_state import GameState
from tests.utils import DummyAI


def play_action(state, player, card):
    player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


def test_inn_discards_hand_and_draws_equal_cards():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([])

    inn = get_card("Inn")
    starting_hand = [inn, get_card("Copper"), get_card("Estate")]
    player.hand = starting_hand[:]

    player.deck = [
        get_card("Copper"),
        get_card("Silver"),
        get_card("Gold"),
        get_card("Estate"),
        get_card("Village"),
        get_card("Smithy"),
    ]

    play_action(state, player, inn)

    assert [card.name for card in player.discard] == [
        "Copper",
        "Estate",
        "Smithy",
        "Village",
    ]
    assert [card.name for card in player.hand] == [
        "Estate",
        "Gold",
        "Silver",
        "Copper",
    ]
    assert inn in player.in_play

