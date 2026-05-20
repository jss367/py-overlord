"""Reinforcement learning components for Dominion."""

from dominion.rl.random_ai import RandomAI
from dominion.rl.rl_ai import RLAI


def __getattr__(name):
    if name == "DominionEnv":
        from dominion.rl.env import DominionEnv

        return DominionEnv
    if name == "MLPPolicy":
        from dominion.rl.networks import MLPPolicy

        return MLPPolicy
    if name == "PPOTrainer":
        from dominion.rl.ppo import PPOTrainer

        return PPOTrainer
    if name in {"StateEncoder", "PHASE1_KINGDOM"}:
        from dominion.rl.state_encoder import PHASE1_KINGDOM, StateEncoder

        return {"StateEncoder": StateEncoder, "PHASE1_KINGDOM": PHASE1_KINGDOM}[name]
    if name == "ActionEncoder":
        from dominion.rl.action_encoder import ActionEncoder

        return ActionEncoder
    raise AttributeError(f"module 'dominion.rl' has no attribute {name!r}")

__all__ = [
    "DominionEnv",
    "MLPPolicy",
    "PPOTrainer",
    "RandomAI",
    "RLAI",
    "StateEncoder",
    "ActionEncoder",
    "PHASE1_KINGDOM",
]
