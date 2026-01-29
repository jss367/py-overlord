"""Tests for state encoder."""

import numpy as np
import pytest
from dominion.rl.state_encoder import StateEncoder, PHASE1_KINGDOM
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.rl.rl_ai import RLAI
from dominion.rl.random_ai import RandomAI
from dominion.cards.registry import get_card


class TestStateEncoder:
    """Tests for StateEncoder."""

    def test_phase1_kingdom_defined(self):
        """Phase 1 kingdom should be defined."""
        assert len(PHASE1_KINGDOM) == 4
        assert "Village" in PHASE1_KINGDOM
        assert "Smithy" in PHASE1_KINGDOM

    def test_encoder_initialization(self):
        """Encoder should initialize with kingdom cards."""
        encoder = StateEncoder(PHASE1_KINGDOM)
        assert encoder.observation_size > 0

    def test_encode_returns_numpy_array(self):
        """encode() should return a numpy array."""
        encoder = StateEncoder(PHASE1_KINGDOM)

        # Set up minimal game state
        game_state = GameState(players=[], supply={})
        kingdom_cards = [get_card(name) for name in PHASE1_KINGDOM]
        game_state.initialize_game(
            [RLAI(), RandomAI()],
            kingdom_cards,
        )

        obs = encoder.encode(game_state, player_index=0)
        assert isinstance(obs, np.ndarray)
        assert obs.dtype == np.float32

    def test_encode_correct_size(self):
        """encode() should return array of correct size."""
        encoder = StateEncoder(PHASE1_KINGDOM)

        game_state = GameState(players=[], supply={})
        kingdom_cards = [get_card(name) for name in PHASE1_KINGDOM]
        game_state.initialize_game(
            [RLAI(), RandomAI()],
            kingdom_cards,
        )

        obs = encoder.encode(game_state, player_index=0)
        assert obs.shape == (encoder.observation_size,)

    def test_encode_contains_hand_info(self):
        """Encoded state should reflect hand contents."""
        encoder = StateEncoder(PHASE1_KINGDOM)

        game_state = GameState(players=[], supply={})
        kingdom_cards = [get_card(name) for name in PHASE1_KINGDOM]
        game_state.initialize_game(
            [RLAI(), RandomAI()],
            kingdom_cards,
        )

        # Player starts with Coppers and Estates in hand
        obs = encoder.encode(game_state, player_index=0)

        # Should be non-zero somewhere (hand counts are encoded)
        assert np.any(obs != 0)

    def test_encode_contains_resources(self):
        """Encoded state should include current resources."""
        encoder = StateEncoder(PHASE1_KINGDOM)

        game_state = GameState(players=[], supply={})
        kingdom_cards = [get_card(name) for name in PHASE1_KINGDOM]
        game_state.initialize_game(
            [RLAI(), RandomAI()],
            kingdom_cards,
        )

        # Modify resources
        game_state.current_player.actions = 3
        game_state.current_player.coins = 5

        obs = encoder.encode(game_state, player_index=0)

        # Resources are in first few positions
        # actions, buys, coins are normalized
        assert obs[0] > 0  # actions > 1

    def test_different_states_different_encodings(self):
        """Different game states should produce different encodings."""
        encoder = StateEncoder(PHASE1_KINGDOM)

        # First game
        game_state1 = GameState(players=[], supply={})
        kingdom_cards = [get_card(name) for name in PHASE1_KINGDOM]
        game_state1.initialize_game([RLAI(), RandomAI()], kingdom_cards)

        # Second game with modified state
        game_state2 = GameState(players=[], supply={})
        game_state2.initialize_game([RLAI(), RandomAI()], kingdom_cards)
        game_state2.current_player.coins = 10

        obs1 = encoder.encode(game_state1, player_index=0)
        obs2 = encoder.encode(game_state2, player_index=0)

        assert not np.array_equal(obs1, obs2)
