"""Training script for RL Dominion agent."""

import argparse
from datetime import datetime
from pathlib import Path

from dominion.rl.env import DominionEnv
from dominion.rl.ppo import PPOTrainer
from dominion.rl.state_encoder import PHASE1_KINGDOM


def train(
    num_iterations: int = 1000,
    rollout_steps: int = 2048,
    save_freq: int = 100,
    log_freq: int = 10,
    checkpoint_dir: str = "checkpoints",
):
    """Train an RL agent on Dominion."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = Path(checkpoint_dir) / f"run_{timestamp}"
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"Training RL Dominion agent")
    print(f"Kingdom: {PHASE1_KINGDOM}")
    print(f"Checkpoints: {save_dir}")
    print(f"Iterations: {num_iterations}, Rollout steps: {rollout_steps}")
    print()

    env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)
    trainer = PPOTrainer(env, rollout_steps=rollout_steps)

    for iteration in range(1, num_iterations + 1):
        metrics = trainer.train_iteration()

        if iteration % log_freq == 0:
            print(
                f"Iter {iteration:5d} | "
                f"P.Loss: {metrics['policy_loss']:.4f} | "
                f"V.Loss: {metrics['value_loss']:.4f} | "
                f"Entropy: {metrics['entropy']:.4f} | "
                f"Win Rate: {metrics['win_rate']:.1%} | "
                f"Ep.Reward: {metrics['mean_episode_reward']:.3f}"
            )

        if iteration % save_freq == 0:
            checkpoint_path = save_dir / f"checkpoint_{iteration:06d}.pt"
            trainer.save(str(checkpoint_path))
            print(f"  Saved: {checkpoint_path}")

    # Final save
    final_path = save_dir / "final.pt"
    trainer.save(str(final_path))
    print(f"\nTraining complete. Final model: {final_path}")

    env.close()
    return str(final_path)


def main():
    parser = argparse.ArgumentParser(description="Train RL Dominion agent")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--rollout-steps", type=int, default=2048)
    parser.add_argument("--save-freq", type=int, default=100)
    parser.add_argument("--log-freq", type=int, default=10)
    parser.add_argument("--checkpoint-dir", type=str, default="checkpoints")

    args = parser.parse_args()
    train(
        num_iterations=args.iterations,
        rollout_steps=args.rollout_steps,
        save_freq=args.save_freq,
        log_freq=args.log_freq,
        checkpoint_dir=args.checkpoint_dir,
    )


if __name__ == "__main__":
    main()
