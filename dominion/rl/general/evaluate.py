"""Seat-paired held-out evaluation; no training or checkpoint selection here."""

import argparse
import hashlib
import json
from pathlib import Path
import random

import numpy as np
import torch

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.rl.env import episode_status, game_reward
from dominion.rl.general.encoding import source_fingerprint, validate_kingdom
from dominion.rl.general.opponents import BASELINES, make_opponent
from dominion.rl.general.policy import GeneralAI, load_checkpoint


def play_game(kingdom, agent, opponent, seed, seat, max_turns=100):
    validate_kingdom(kingdom)
    random.seed(seed)
    state = GameState(players=[], supply={})
    state.log_callback = lambda msg: None
    ais = [agent, opponent] if seat == 0 else [opponent, agent]
    state.initialize_game(ais, [get_card(n) for n in kingdom])
    while True:
        terminated, truncated = episode_status(state, max_turns)
        if terminated or truncated:
            break
        state.play_turn()
    return {"reward": None if truncated else game_reward(state, seat),
            "truncated": truncated,
            "vp": state.players[seat].get_victory_points(),
            "opponent_vp": state.players[1 - seat].get_victory_points(),
            "turns": state.turn_number}


def summarize(games):
    finished = [g for g in games if not g["truncated"]]
    wins = sum(g["reward"] == 1 for g in finished)
    ties = sum(g["reward"] == 0 for g in finished)
    return {"games": len(games), "wins": wins,
            "losses": sum(g["reward"] == -1 for g in finished), "ties": ties,
            "truncated": len(games) - len(finished),
            # A cap is a failure to finish, scored zero rather than as a draw.
            "score_rate": (wins + ties / 2) / len(games),
            "mean_vp": float(np.mean([g["vp"] for g in games])),
            "mean_opponent_vp": float(np.mean([g["opponent_vp"] for g in games]))}


def evaluate_policy(policy, kingdoms, pairs=20, seed=900_000, baselines=BASELINES, max_turns=100):
    if pairs < 1 or not kingdoms or max_turns < 1:
        raise ValueError("Evaluation needs kingdoms, positive pairs and positive max_turns")
    policy.eval()
    rows, totals = [], {}
    for baseline in baselines:
        all_games, board_scores = [], []
        for board_index, kingdom in enumerate(kingdoms):
            games = []
            for pair in range(pairs):
                game_seed = seed + board_index * 100_000 + pair
                for seat in (0, 1):
                    game = play_game(kingdom, GeneralAI(policy), make_opponent(baseline, kingdom),
                                     game_seed, seat, max_turns)
                    game.update(seed=game_seed, seat=seat)
                    games.append(game)
            result = summarize(games)
            board_scores.append(result["score_rate"])
            rows.append({"baseline": baseline, "kingdom": list(kingdom),
                         "opponent_strategy": make_opponent(baseline, kingdom).strategy.name,
                         **result, "individual_games": games})
            all_games.extend(games)
        total = summarize(all_games)
        # Resample entire kingdoms, preserving within-board and seat-pair dependence.
        if len(board_scores) > 1:
            rng = np.random.default_rng(seed)
            samples = rng.choice(board_scores, size=(5000, len(board_scores)), replace=True).mean(1)
            total["kingdom_bootstrap_95_interval"] = np.quantile(samples, [.025, .975]).tolist()
        totals[baseline] = total
    return {"pairs_per_kingdom": pairs, "seed": seed, "max_turns": max_turns,
            "policy_action_selection": "greedy", "totals": totals, "kingdom_results": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--pairs", type=int, default=20)
    parser.add_argument("--split", choices=("validation", "test"), default="test")
    parser.add_argument("--seed", type=int, default=900_000)
    parser.add_argument("--max-turns", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    policy, metadata = load_checkpoint(args.checkpoint)
    result = evaluate_policy(policy, metadata["splits"][args.split], args.pairs,
                             args.seed, max_turns=args.max_turns)
    result.update(split=args.split, checkpoint=str(args.checkpoint),
                  checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                  evaluation_source_fingerprint=source_fingerprint(),
                  engine_losing_purchase_filter=False,
                  training_metadata=metadata)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["totals"], indent=2))


if __name__ == "__main__":
    main()
