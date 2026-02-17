"""Neural network architectures for RL agents."""

import torch
import torch.nn as nn
from torch.distributions import Categorical


class MLPPolicy(nn.Module):
    """Simple MLP policy and value network.

    Architecture:
    - Shared MLP trunk: obs -> hidden -> hidden
    - Policy head: hidden -> action_logits
    - Value head: hidden -> scalar value
    """

    def __init__(
        self,
        obs_size: int,
        action_size: int,
        hidden_size: int = 256,
    ):
        super().__init__()

        self.shared = nn.Sequential(
            nn.Linear(obs_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
        )

        self.policy_head = nn.Linear(hidden_size, action_size)
        self.value_head = nn.Linear(hidden_size, 1)

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Forward pass returning logits and value.

        Args:
            obs: Observation tensor of shape (batch, obs_size).

        Returns:
            Tuple of (action_logits, value) tensors.
        """
        hidden = self.shared(obs)
        logits = self.policy_head(hidden)
        value = self.value_head(hidden)
        return logits, value

    def get_action(
        self,
        obs: torch.Tensor,
        action_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Sample an action from the policy.

        Args:
            obs: Observation tensor of shape (batch, obs_size).
            action_mask: Boolean mask of valid actions (batch, action_size).

        Returns:
            Tuple of (action, log_prob, value).
        """
        logits, value = self.forward(obs)

        # Mask invalid actions with large negative value
        masked_logits = logits.clone()
        masked_logits[~action_mask] = float("-inf")

        dist = Categorical(logits=masked_logits)
        action = dist.sample()
        log_prob = dist.log_prob(action)

        return action, log_prob, value

    def evaluate_actions(
        self,
        obs: torch.Tensor,
        actions: torch.Tensor,
        action_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Evaluate actions for PPO update.

        Args:
            obs: Observations (batch, obs_size).
            actions: Actions taken (batch,).
            action_mask: Valid action mask (batch, action_size).

        Returns:
            Tuple of (log_probs, entropy, values).
        """
        logits, value = self.forward(obs)

        masked_logits = logits.clone()
        masked_logits[~action_mask] = float("-inf")

        dist = Categorical(logits=masked_logits)
        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()

        return log_probs, entropy, value
