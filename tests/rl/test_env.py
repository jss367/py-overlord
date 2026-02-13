"""Tests for DominionEnv Gym environment."""

import numpy as np
import pytest
import gymnasium as gym
from dominion.rl.env import DominionEnv
from dominion.rl.state_encoder import PHASE1_KINGDOM


class TestDominionEnv:
    """Tests for DominionEnv."""

    def test_env_creation(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        assert env is not None

    def test_env_has_observation_space(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        assert hasattr(env, "observation_space")
        assert isinstance(env.observation_space, gym.spaces.Box)

    def test_env_has_action_space(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        assert hasattr(env, "action_space")
        assert isinstance(env.action_space, gym.spaces.Discrete)

    def test_reset_returns_observation(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        obs, info = env.reset(seed=42)
        assert isinstance(obs, np.ndarray)
        assert obs.shape == env.observation_space.shape
        assert isinstance(info, dict)
        env.close()

    def test_reset_returns_valid_mask(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        obs, info = env.reset(seed=42)
        assert "action_mask" in info
        assert isinstance(info["action_mask"], np.ndarray)
        assert info["action_mask"].shape == (env.action_space.n,)
        assert info["action_mask"].any()  # At least one valid action
        env.close()

    def test_step_returns_correct_tuple(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        obs, info = env.reset(seed=42)

        valid_actions = np.where(info["action_mask"])[0]
        action = valid_actions[0]

        result = env.step(action)
        assert len(result) == 5
        obs, reward, terminated, truncated, info = result
        assert isinstance(obs, np.ndarray)
        assert isinstance(reward, (int, float))
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)
        env.close()

    def test_game_terminates(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        obs, info = env.reset(seed=42)

        terminated = False
        truncated = False
        steps = 0
        max_steps = 50000

        while not (terminated or truncated) and steps < max_steps:
            valid_actions = np.where(info["action_mask"])[0]
            action = valid_actions[0]
            obs, reward, terminated, truncated, info = env.step(action)
            steps += 1

        assert terminated or truncated, f"Game did not end after {steps} steps"
        env.close()

    def test_reward_on_termination(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)

        # Run several games to ensure at least one has a non-zero reward
        any_nonzero = False
        for seed in range(10):
            obs, info = env.reset(seed=seed)
            terminated = False
            truncated = False

            while not (terminated or truncated):
                valid_actions = np.where(info["action_mask"])[0]
                action = valid_actions[0]
                obs, reward, terminated, truncated, info = env.step(action)
                if reward != 0:
                    any_nonzero = True

        assert any_nonzero, "No game produced a non-zero reward across 10 seeds"
        env.close()

    def test_multiple_resets(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        for i in range(3):
            obs, info = env.reset(seed=i)
            assert obs is not None
            assert info["action_mask"].any()
        env.close()

    def test_seed_produces_reproducible_games(self):
        env1 = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        env2 = DominionEnv(kingdom_cards=PHASE1_KINGDOM)

        obs1, _ = env1.reset(seed=12345)
        obs2, _ = env2.reset(seed=12345)

        np.testing.assert_array_equal(obs1, obs2)
        env1.close()
        env2.close()
