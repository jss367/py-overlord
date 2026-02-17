"""Evaluation script for trained RL agents."""

import argparse

import numpy as np
import torch

from dominion.rl.env import DominionEnv
from dominion.rl.networks import MLPPolicy
from dominion.rl.state_encoder import PHASE1_KINGDOM


def evaluate(
    checkpoint_path: str,
    num_games: int = 100,
    verbose: bool = False,
):
    """Evaluate a trained agent against RandomAI."""
    print(f"Evaluating: {checkpoint_path}")
    print(f"Games: {num_games}")
    print()

    env = DominionEnv(kingdom_cards=PHASE1_KINGDOM)

    # Load policy
    policy = MLPPolicy(
        obs_size=env.observation_space.shape[0],
        action_size=env.action_space.n,
    )
    checkpoint = torch.load(checkpoint_path, weights_only=True)
    policy.load_state_dict(checkpoint["policy_state_dict"])
    policy.eval()

    wins = 0
    losses = 0
    ties = 0
    total_vp = 0
    total_opp_vp = 0

    for game_num in range(num_games):
        obs, info = env.reset(seed=game_num)
        terminated = False
        truncated = False
        reward = 0.0

        while not (terminated or truncated):
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0)
            mask_tensor = torch.BoolTensor(info["action_mask"]).unsqueeze(0)

            with torch.no_grad():
                action, _, _ = policy.get_action(obs_tensor, mask_tensor)

            obs, reward, terminated, truncated, info = env.step(action.item())

        rl_vp = env.game_state.players[0].get_victory_points()
        opp_vp = env.game_state.players[1].get_victory_points()
        total_vp += rl_vp
        total_opp_vp += opp_vp

        if reward > 0:
            wins += 1
            result = "WIN"
        elif reward < 0:
            losses += 1
            result = "LOSS"
        else:
            ties += 1
            result = "TIE"

        if verbose:
            print(f"Game {game_num + 1}: {result} ({rl_vp} vs {opp_vp})")

    env.close()

    print("\n=== Results ===")
    print(f"Wins:   {wins:4d} ({100*wins/num_games:.1f}%)")
    print(f"Losses: {losses:4d} ({100*losses/num_games:.1f}%)")
    print(f"Ties:   {ties:4d} ({100*ties/num_games:.1f}%)")
    print(f"Avg VP (Agent):  {total_vp/num_games:.1f}")
    print(f"Avg VP (Random): {total_opp_vp/num_games:.1f}")

    return wins / num_games


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained RL agent")
    parser.add_argument("checkpoint", type=str)
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    evaluate(
        checkpoint_path=args.checkpoint,
        num_games=args.games,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
