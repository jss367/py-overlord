"""PPO training implementation for Dominion."""

from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.optim import Adam

from dominion.rl.env import DominionEnv
from dominion.rl.networks import MLPPolicy


class PPOTrainer:
    """Proximal Policy Optimization trainer.

    Implements the PPO-Clip algorithm with action masking.
    """

    def __init__(
        self,
        env: DominionEnv,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        rollout_steps: int = 2048,
        ppo_epochs: int = 10,
        batch_size: int = 64,
        device: str = "cpu",
    ):
        self.env = env
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        self.rollout_steps = rollout_steps
        self.ppo_epochs = ppo_epochs
        self.batch_size = batch_size
        self.device = torch.device(device)

        # Create policy network
        self.policy = MLPPolicy(
            obs_size=env.observation_space.shape[0],
            action_size=env.action_space.n,
        ).to(self.device)

        self.optimizer = Adam(self.policy.parameters(), lr=lr)

        # Current state
        self._obs: Optional[np.ndarray] = None
        self._info: Optional[dict] = None
        self._reset_env()

        # Stats
        self._episode_rewards: list[float] = []
        self._current_episode_reward: float = 0.0

    def _reset_env(self) -> None:
        self._obs, self._info = self.env.reset()
        self._current_episode_reward = 0.0

    def collect_rollout(self) -> dict[str, Any]:
        """Collect rollout data from environment."""
        obs_list = []
        actions_list = []
        rewards_list = []
        dones_list = []
        log_probs_list = []
        values_list = []
        masks_list = []

        for _ in range(self.rollout_steps):
            obs_tensor = torch.FloatTensor(self._obs).unsqueeze(0).to(self.device)
            mask_tensor = torch.BoolTensor(self._info["action_mask"]).unsqueeze(0).to(self.device)

            with torch.no_grad():
                action, log_prob, value = self.policy.get_action(obs_tensor, mask_tensor)

            action_np = action.cpu().numpy()[0]

            # Store data
            obs_list.append(self._obs.copy())
            masks_list.append(self._info["action_mask"].copy())
            actions_list.append(action_np)
            log_probs_list.append(log_prob.cpu().numpy()[0])
            values_list.append(value.cpu().numpy()[0, 0])

            # Step environment
            next_obs, reward, terminated, truncated, info = self.env.step(action_np)
            done = terminated or truncated

            rewards_list.append(reward)
            dones_list.append(done)
            self._current_episode_reward += reward

            if done:
                self._episode_rewards.append(self._current_episode_reward)
                self._obs, self._info = self.env.reset()
                self._current_episode_reward = 0.0
            else:
                self._obs = next_obs
                self._info = info

        return {
            "obs": np.array(obs_list),
            "actions": np.array(actions_list),
            "rewards": np.array(rewards_list),
            "dones": np.array(dones_list),
            "log_probs": np.array(log_probs_list),
            "values": np.array(values_list),
            "masks": np.array(masks_list),
        }

    def compute_advantages(
        self, rollout: dict[str, Any]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute GAE advantages and returns."""
        rewards = rollout["rewards"]
        dones = rollout["dones"]
        values = rollout["values"]

        advantages = np.zeros_like(rewards)
        returns = np.zeros_like(rewards)

        # Get bootstrap value for last state
        with torch.no_grad():
            obs_tensor = torch.FloatTensor(self._obs).unsqueeze(0).to(self.device)
            _, last_value = self.policy(obs_tensor)
            last_value = last_value.cpu().numpy()[0, 0]

        # GAE computation (reversed)
        gae = 0.0
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = last_value
            else:
                next_value = values[t + 1]

            next_non_terminal = 1.0 - float(dones[t])
            delta = rewards[t] + self.gamma * next_value * next_non_terminal - values[t]
            gae = delta + self.gamma * self.gae_lambda * next_non_terminal * gae
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]

        return advantages, returns

    def ppo_update(
        self,
        rollout: dict[str, Any],
        advantages: np.ndarray,
        returns: np.ndarray,
    ) -> dict[str, float]:
        """Perform PPO update."""
        obs = torch.FloatTensor(rollout["obs"]).to(self.device)
        actions = torch.LongTensor(rollout["actions"]).to(self.device)
        old_log_probs = torch.FloatTensor(rollout["log_probs"]).to(self.device)
        masks = torch.BoolTensor(rollout["masks"]).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        returns_t = torch.FloatTensor(returns).to(self.device)

        # Normalize advantages
        advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)

        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0
        num_updates = 0

        num_samples = len(obs)
        indices = np.arange(num_samples)

        for _ in range(self.ppo_epochs):
            np.random.shuffle(indices)

            for start in range(0, num_samples, self.batch_size):
                end = start + self.batch_size
                batch_indices = indices[start:end]

                batch_obs = obs[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_masks = masks[batch_indices]
                batch_advantages = advantages_t[batch_indices]
                batch_returns = returns_t[batch_indices]

                # Evaluate actions
                log_probs, entropy, values = self.policy.evaluate_actions(
                    batch_obs, batch_actions, batch_masks
                )
                values = values.squeeze(-1)

                # Policy loss (PPO-Clip)
                ratio = torch.exp(log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * batch_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss
                value_loss = nn.functional.mse_loss(values, batch_returns)

                # Entropy bonus
                entropy_loss = -entropy.mean()

                # Total loss
                loss = (
                    policy_loss
                    + self.value_coef * value_loss
                    + self.entropy_coef * entropy_loss
                )

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
                self.optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += -entropy_loss.item()
                num_updates += 1

        return {
            "policy_loss": total_policy_loss / max(num_updates, 1),
            "value_loss": total_value_loss / max(num_updates, 1),
            "entropy": total_entropy / max(num_updates, 1),
        }

    def train_iteration(self) -> dict[str, float]:
        """Run one training iteration."""
        rollout = self.collect_rollout()
        advantages, returns = self.compute_advantages(rollout)
        loss_info = self.ppo_update(rollout, advantages, returns)

        # Add rollout stats
        loss_info["mean_reward"] = rollout["rewards"].mean()
        episodes_completed = rollout["dones"].sum()
        loss_info["episodes_completed"] = int(episodes_completed)

        if self._episode_rewards:
            recent = self._episode_rewards[-100:]
            loss_info["mean_episode_reward"] = sum(recent) / len(recent)
            loss_info["win_rate"] = sum(1 for r in recent if r > 0) / len(recent)
        else:
            loss_info["mean_episode_reward"] = 0.0
            loss_info["win_rate"] = 0.0

        return loss_info

    def save(self, path: str) -> None:
        """Save model checkpoint."""
        torch.save({
            "policy_state_dict": self.policy.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
        }, path)

    def load(self, path: str) -> None:
        """Load model checkpoint."""
        checkpoint = torch.load(path, weights_only=True)
        self.policy.load_state_dict(checkpoint["policy_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
