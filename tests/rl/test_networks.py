"""Tests for neural network components."""

import pytest
import torch
from dominion.rl.networks import MLPPolicy
from dominion.rl.state_encoder import PHASE1_KINGDOM, StateEncoder
from dominion.rl.action_encoder import ActionEncoder


class TestMLPPolicy:
    """Tests for MLP policy network."""

    def test_initialization(self):
        encoder = StateEncoder(PHASE1_KINGDOM)
        action_encoder = ActionEncoder(PHASE1_KINGDOM)
        policy = MLPPolicy(
            obs_size=encoder.observation_size,
            action_size=action_encoder.action_size,
        )
        assert policy is not None

    def test_forward_returns_logits_and_value(self):
        encoder = StateEncoder(PHASE1_KINGDOM)
        action_encoder = ActionEncoder(PHASE1_KINGDOM)
        policy = MLPPolicy(
            obs_size=encoder.observation_size,
            action_size=action_encoder.action_size,
        )

        obs = torch.randn(1, encoder.observation_size)
        logits, value = policy(obs)

        assert logits.shape == (1, action_encoder.action_size)
        assert value.shape == (1, 1)

    def test_batch_forward(self):
        encoder = StateEncoder(PHASE1_KINGDOM)
        action_encoder = ActionEncoder(PHASE1_KINGDOM)
        policy = MLPPolicy(
            obs_size=encoder.observation_size,
            action_size=action_encoder.action_size,
        )

        batch_size = 32
        obs = torch.randn(batch_size, encoder.observation_size)
        logits, value = policy(obs)

        assert logits.shape == (batch_size, action_encoder.action_size)
        assert value.shape == (batch_size, 1)

    def test_get_action_with_mask(self):
        encoder = StateEncoder(PHASE1_KINGDOM)
        action_encoder = ActionEncoder(PHASE1_KINGDOM)
        policy = MLPPolicy(
            obs_size=encoder.observation_size,
            action_size=action_encoder.action_size,
        )

        obs = torch.randn(1, encoder.observation_size)

        # Create mask that only allows action 0
        mask = torch.zeros(1, action_encoder.action_size, dtype=torch.bool)
        mask[0, 0] = True

        action, log_prob, value = policy.get_action(obs, mask)

        assert action.item() == 0  # Only valid action
        assert log_prob.shape == (1,)
        assert value.shape == (1, 1)

    def test_evaluate_actions(self):
        encoder = StateEncoder(PHASE1_KINGDOM)
        action_encoder = ActionEncoder(PHASE1_KINGDOM)
        policy = MLPPolicy(
            obs_size=encoder.observation_size,
            action_size=action_encoder.action_size,
        )

        obs = torch.randn(4, encoder.observation_size)
        actions = torch.tensor([0, 1, 2, 0])
        mask = torch.ones(4, action_encoder.action_size, dtype=torch.bool)

        log_probs, entropy, values = policy.evaluate_actions(obs, actions, mask)

        assert log_probs.shape == (4,)
        assert entropy.shape == (4,)
        assert values.shape == (4, 1)
