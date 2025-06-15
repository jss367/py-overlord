from dominion.cards.registry import get_card
from dominion.game.player_state import PlayerState
from dominion.game.game_state import GameState
from tests.utils import DummyAI, ChooseFirstActionAI


def play_action(state, player, card):
    player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


def test_acting_troupe_gives_villagers_and_trashes():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([])

    troupe = get_card("Acting Troupe")
    player.hand = [troupe]
    play_action(state, player, troupe)

    assert player.villagers == 4
    assert troupe in state.trash
    assert troupe not in player.in_play


def test_villagers_can_be_spent_for_actions():
    ai = ChooseFirstActionAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([])

    player.hand = [get_card("Village")]
    player.actions = 0
    player.villagers = 1
    state.phase = "action"
    state.handle_action_phase()

    assert player.villagers == 0
    assert player.actions == 2
