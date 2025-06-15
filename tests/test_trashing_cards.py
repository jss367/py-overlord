import pytest
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.cards.registry import get_card
from tests.utils import TrashFirstAI


def play_action(state, player, card):
    """Helper to play an action card from hand."""
    player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


def test_expand_trashes_card_and_triggers_on_trash():
    ai = TrashFirstAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Expand"), get_card("Village")])

    # Ensure deck has a card to draw when Rats is trashed
    player.deck = [get_card("Copper")]
    player.hand = [get_card("Expand"), get_card("Rats")]

    expand = player.hand[0]
    play_action(state, player, expand)

    # Rats should be trashed and its on_trash draws a card
    assert any(c.name == "Rats" for c in state.trash)
    assert len(player.hand) == 1  # drew back up to one card


def test_mint_on_gain_trashes_treasures_in_play():
    ai = TrashFirstAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Mint")])

    player.in_play = [get_card("Copper"), get_card("Silver")]
    mint = get_card("Mint")
    mint.on_gain(state, player)

    assert len(state.trash) == 2
    assert not player.in_play


def test_loan_trashes_first_treasure():
    ai = TrashFirstAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([])

    player.deck = [get_card("Silver"), get_card("Estate")]
    loan = get_card("Loan")
    player.hand = [loan]
    play_action(state, player, loan)

    assert any(c.name == "Silver" for c in state.trash)
    assert all(c.name != "Silver" for c in player.discard)



def test_forager_trashes_card():
    ai = TrashFirstAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Forager")])

    player.deck = [get_card("Copper")]
    player.hand = [get_card("Forager"), get_card("Rats")]

    forager = player.hand[0]
    play_action(state, player, forager)

    assert any(c.name == "Rats" for c in state.trash)
    assert len(player.hand) == 1  # Rats drew a card on trash
