"""Tests for the Training event +$1 token bonus."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


def setup_state():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")])
    player = state.players[0]
    return state, player


def test_training_adds_coin_when_playing_trained_pile():
    """Playing a card from the trained pile should give +$1."""
    state, player = setup_state()

    village = get_card("Village")
    player.hand = [village] + [get_card("Copper") for _ in range(4)]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.actions = 1
    player.coins = 0
    player.training_pile = "Village"

    state.phase = "action"
    state.handle_action_phase()

    # Village gives +2 actions, 0 coins. Training should add +$1.
    assert player.coins == 1


def test_training_bonus_applies_per_flagship_replay():
    """When Flagship replays a trained card, Training bonus should apply each time."""
    state, player = setup_state()

    # Add Flagship to kingdom
    state.supply["Flagship"] = 10

    flagship = get_card("Flagship")
    village = get_card("Village")
    player.hand = [flagship, village] + [get_card("Copper") for _ in range(3)]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.actions = 2
    player.coins = 0
    player.training_pile = "Village"

    state.phase = "action"
    state.handle_action_phase()

    # Flagship gives +$2. Village replayed 2x (original + flagship).
    # Training should give +$1 per play = +$2.
    # Total: $2 (Flagship) + $2 (Training 2x) = $4.
    assert player.coins == 4
