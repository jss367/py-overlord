"""Tests for PPO training."""

import pytest
import torch
from dominion.rl.ppo import PPOTrainer
from dominion.rl.env import DominionEnv
from dominion.rl.state_encoder import PHASE1_KINGDOM


class TestPPOTrainer:
    """Tests for PPO trainer."""

    def test_initialization(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        trainer = PPOTrainer(env, rollout_steps=50)
        assert trainer is not None
        env.close()

    def test_collect_rollout(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        trainer = PPOTrainer(env, rollout_steps=50)

        rollout = trainer.collect_rollout()

        assert "obs" in rollout
        assert "actions" in rollout
        assert "rewards" in rollout
        assert "dones" in rollout
        assert "log_probs" in rollout
        assert "values" in rollout
        assert "masks" in rollout

        assert len(rollout["obs"]) == 50
        assert len(rollout["actions"]) == 50
        env.close()

    def test_compute_advantages(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        trainer = PPOTrainer(env, rollout_steps=50)

        rollout = trainer.collect_rollout()
        advantages, returns = trainer.compute_advantages(rollout)

        assert advantages.shape[0] == 50
        assert returns.shape[0] == 50
        env.close()

    def test_ppo_update(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        trainer = PPOTrainer(env, rollout_steps=50, ppo_epochs=2, batch_size=16)

        rollout = trainer.collect_rollout()
        advantages, returns = trainer.compute_advantages(rollout)
        loss_info = trainer.ppo_update(rollout, advantages, returns)

        assert "policy_loss" in loss_info
        assert "value_loss" in loss_info
        assert "entropy" in loss_info
        env.close()

    def test_train_one_iteration(self):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        trainer = PPOTrainer(env, rollout_steps=50)

        info = trainer.train_iteration()

        assert "policy_loss" in info
        assert "value_loss" in info
        assert "mean_reward" in info
        env.close()

    def test_save_and_load(self, tmp_path):
        env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        trainer = PPOTrainer(env, rollout_steps=50)

        # Train a bit
        trainer.train_iteration()

        # Save
        path = str(tmp_path / "test_checkpoint.pt")
        trainer.save(path)

        # Load into new trainer
        env2 = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
        trainer2 = PPOTrainer(env2, rollout_steps=50)
        trainer2.load(path)

        # Verify weights match
        for p1, p2 in zip(trainer.policy.parameters(), trainer2.policy.parameters()):
            assert torch.allclose(p1, p2)

        env.close()
        env2.close()


@pytest.mark.parametrize(
    'terminated,truncated,reward,expected_return',
    [(False, True, 0.0, 6.3), (True, False, 1.0, 1.0), (False, False, 0.0, 6.3)],
)
def test_rollout_bootstraps_final_observation_before_reset(terminated, truncated, reward, expected_return):
    import numpy as np
    from types import SimpleNamespace
    from dominion.rl.networks import MLPPolicy

    class BoundaryEnv:
        observation_space = SimpleNamespace(shape=(1,))
        action_space = SimpleNamespace(n=1)
        resets = 0

        def reset(self, **kwargs):
            self.resets += 1
            return np.array([2.0 if self.resets == 1 else 100.0], dtype=np.float32), {
                'action_mask': np.array([True])}

        def step(self, action):
            return np.array([7.0], dtype=np.float32), reward, terminated, truncated, {
                'action_mask': np.array([True])}

    policy = MLPPolicy(1, 1, hidden_size=2)
    policy.forward = lambda obs: (torch.zeros((len(obs), 1)), obs[:, :1])
    env = BoundaryEnv()
    trainer = PPOTrainer(env, policy=policy, rollout_steps=1, gamma=.9)
    rollout = trainer.collect_rollout()
    assert rollout['terminated'].tolist() == [terminated]
    assert rollout['truncated'].tolist() == [truncated]
    assert env.resets == (2 if terminated or truncated else 1)
    if truncated:
        assert rollout['truncated_values'].tolist() == [7.0]
        assert trainer._obs[0] == 100.0
    _, returns = trainer.compute_advantages(rollout)
    np.testing.assert_allclose(returns, [expected_return])


def test_advantages_stop_at_truncation_without_losing_bootstrap():
    import numpy as np

    # Values in the reset episode are deliberately very different: neither
    # its initial observation nor its advantages may leak into the capped one.
    trainer = object.__new__(PPOTrainer)
    trainer.gamma = .9
    trainer.gae_lambda = .8
    trainer.device = torch.device('cpu')
    trainer._obs = np.array([999.0], dtype=np.float32)
    trainer.policy = lambda obs: (torch.zeros((len(obs), 1)), obs[:, :1])
    rollout = {
        'rewards': np.array([0.0, 0.0, 1.0]),
        'values': np.array([2.0, 4.0, 10.0]),
        'dones': np.array([False, True, True]),
        'terminated': np.array([False, False, True]),
        'truncated': np.array([False, True, False]),
        'truncated_values': np.array([0.0, 7.0, 0.0]),
    }
    advantages, returns = trainer.compute_advantages(rollout)
    np.testing.assert_allclose(advantages, [3.256, 2.3, -9.0])
    np.testing.assert_allclose(returns, [5.256, 6.3, 1.0])
