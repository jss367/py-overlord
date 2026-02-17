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
