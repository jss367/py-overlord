"""Imitation warm start followed by PPO against baselines and frozen peers."""

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import time

import numpy as np
import torch
from torch import nn

from dominion.ai.genetic_ai import GeneticAI
from dominion.rl.action_encoder import ActionEncoder
from dominion.rl.env import DominionEnv
from dominion.rl.general.encoding import (
    CARD_POOL, GeneralEncoder, kingdom_splits, source_fingerprint, validate_splits,
)
from dominion.rl.general.evaluate import evaluate_policy, play_game
from dominion.rl.general.opponents import make_opponent, teacher_strategy
from dominion.rl.general.policy import GeneralAI, GeneralPolicy, load_checkpoint, save_checkpoint
from dominion.rl.ppo import PPOTrainer


class RecordingTeacher(GeneticAI):
    # Recording is a side effect: cloned probes would duplicate the dataset
    # and apply an endgame filter that is absent during PPO.
    decision_hooks_are_pure = False

    def __init__(self, kingdom, examples):
        super().__init__(teacher_strategy(kingdom))
        self.encoder = GeneralEncoder()
        self.actions = ActionEncoder(list(CARD_POOL))
        self.examples = examples

    def record(self, state, choices, decision, choice):
        mask = self.actions.get_action_mask(choices)
        target = self.actions.card_to_action(choice)
        if not mask[target]:
            raise ValueError(f"Teacher chose an illegal {decision} action")
        if mask.sum() > 1:
            seat = next(i for i, p in enumerate(state.players) if p.ai is self)
            self.examples.append((self.encoder.encode_decision(state, seat, decision),
                                  mask, target, decision))
        return choice

    def choose_action(self, state, choices):
        return self.record(state, choices, "action", super().choose_action(state, choices))

    def choose_treasure(self, state, choices):
        return self.record(state, choices, "treasure", super().choose_treasure(state, choices))

    def choose_buy(self, state, choices):
        return self.record(state, choices, "buy", super().choose_buy(state, choices))

    def choose_card_to_trash(self, state, choices):
        return self.record(state, choices, "trash", super().choose_card_to_trash(state, choices))


def collect_examples(kingdoms, games, seed):
    if games < 1:
        raise ValueError("Imitation requires at least one teacher game")
    rng = random.Random(seed)
    examples = []
    for game in range(games):
        kingdom = rng.choice(kingdoms)
        teacher = RecordingTeacher(kingdom, examples)
        opponent = make_opponent(rng.choice(("big_money", "draw_money", "engine")), kingdom)
        play_game(kingdom, teacher, opponent, seed + game, game % 2)
        if (game + 1) % 100 == 0:
            print(f"Teacher games {game + 1}/{games}; examples {len(examples)}", flush=True)
    return examples


def imitate(policy, examples, epochs, seed, batch_size=256):
    obs = torch.from_numpy(np.stack([e[0] for e in examples]))
    masks = torch.from_numpy(np.stack([e[1] for e in examples]))
    targets = torch.tensor([e[2] for e in examples])
    decisions = [e[3] for e in examples]
    # Balance types so playing Treasures cannot drown out buying and trashing.
    counts = Counter(decisions)
    weights = np.asarray([1 / counts[d] for d in decisions])
    weights /= weights.sum()
    rng = np.random.default_rng(seed)
    optimizer = torch.optim.Adam(policy.parameters(), lr=1e-3)
    losses = []
    policy.train()
    for epoch in range(epochs):
        indices = rng.choice(len(examples), size=len(examples), p=weights)
        total = 0.0
        for start in range(0, len(indices), batch_size):
            batch = indices[start:start + batch_size]
            logits, _ = policy(obs[batch])
            logits = logits.masked_fill(~masks[batch], float("-inf"))
            loss = nn.functional.cross_entropy(logits, targets[batch])
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
            optimizer.step()
            total += loss.item() * len(batch)
        losses.append(total / len(examples))
        print(f"Imitation epoch {epoch + 1}/{epochs}: loss {losses[-1]:.4f}", flush=True)
    return losses


class OpponentLeague:
    """Fixed baselines remain in the league as recent frozen peers rotate."""

    def __init__(self, policy, seed):
        self.rng = random.Random(seed)
        self.peers = []
        self.add(policy)

    def add(self, policy):
        snapshot = deepcopy(policy).eval()
        snapshot.requires_grad_(False)
        self.peers.append(snapshot)
        self.peers = self.peers[-4:]

    def __call__(self, kingdom):
        choice = self.rng.choice(("big_money", "draw_money", "engine", "peer"))
        if choice == "peer":
            return GeneralAI(self.rng.choice(self.peers), name="Frozen training peer")
        return make_opponent(choice, kingdom)


def train(output, *, seed=42, teacher_games=600, imitation_epochs=10, iterations=100,
          rollout_steps=2048, validation_every=20, validation_pairs=2, warm_start=None):
    if min(teacher_games, imitation_epochs, rollout_steps, validation_every, validation_pairs) < 1 or iterations < 0:
        raise ValueError("Training counts must be positive (PPO iterations may be zero)")
    started = time.monotonic()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "best.pt").exists():
        raise ValueError("Choose a new output directory to preserve the existing run")
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    splits = kingdom_splits()
    if warm_start:
        policy, previous = load_checkpoint(warm_start)
        splits = previous["splits"]
        imitation = {"warm_start": str(warm_start),
                     "sha256": hashlib.sha256(Path(warm_start).read_bytes()).hexdigest()}
    else:
        policy = GeneralPolicy()
        examples = collect_examples(splits["train"], teacher_games, seed)
        imitation = {"teacher_games": teacher_games, "examples": len(examples),
                     "losses": imitate(policy, examples, imitation_epochs, seed)}
        del examples
    validate_splits(splits)
    metadata = {"created_utc": datetime.now(timezone.utc).isoformat(), "seed": seed,
                "splits": splits, "imitation": imitation,
                "python": platform.python_version(), "torch": str(torch.__version__),
                "source_fingerprint": source_fingerprint(),
                "config": {"iterations": iterations, "rollout_steps": rollout_steps,
                           "validation_every": validation_every, "validation_pairs": validation_pairs,
                           "gamma": .999, "gae_lambda": .97, "learning_rate": 1e-4,
                           "entropy_coef": .002, "ppo_epochs": 4},
                "training_opponents": ["big_money", "draw_money", "engine", "frozen_peers"],
                "ppo_iterations_completed": 0}
    save_checkpoint(output / "imitation.pt", policy, metadata)
    log_path = output / "metrics.jsonl"

    def validate(iteration):
        # Called only after closing the training environment: no interleaved RNG use.
        evaluation = evaluate_policy(policy, splits["validation"], pairs=validation_pairs, seed=700_000)
        rates = {n: r["score_rate"] for n, r in evaluation["totals"].items()}
        score = float(np.mean(list(rates.values())))
        with log_path.open("a") as stream:
            stream.write(json.dumps({"iteration": iteration, "validation": rates, "score": score}) + "\n")
        print(f"Validation at {iteration}: {rates}; mean {score:.3f}", flush=True)
        return score

    best_score = validate(0)
    metadata["validation_score"] = best_score
    save_checkpoint(output / "best.pt", policy, metadata)
    league = OpponentLeague(policy, seed + 1)
    env = DominionEnv(splits["train"][0], league, kingdoms=splits["train"],
                      vocabulary=CARD_POOL, state_encoder=GeneralEncoder(), randomize_seats=True)
    trainer = None
    try:
        if iterations:
            trainer = PPOTrainer(env, policy=policy, seed=seed, rollout_steps=rollout_steps,
                                 ppo_epochs=4, batch_size=256, gamma=.999, gae_lambda=.97,
                                 lr=1e-4, entropy_coef=.002)
        for iteration in range(1, iterations + 1):
            policy.train()
            metrics = trainer.train_iteration()
            with log_path.open("a") as stream:
                stream.write(json.dumps({"iteration": iteration,
                                         **{k: float(v) for k, v in metrics.items()}}) + "\n")
            if iteration % 5 == 0:
                print(f"PPO {iteration}/{iterations}: training win rate {metrics['win_rate']:.3f}", flush=True)
            metadata["ppo_iterations_completed"] = iteration
            if iteration % validation_every == 0 or iteration == iterations:
                env.close()
                score = validate(iteration)
                metadata["validation_score"] = score
                if score > best_score:
                    best_score = score
                    save_checkpoint(output / "best.pt", policy, metadata, trainer.optimizer)
                league.add(policy)
                save_checkpoint(output / "latest.pt", policy, metadata, trainer.optimizer)
                if iteration != iterations:
                    trainer._obs, trainer._info = env.reset(seed=seed + iteration)
                    trainer._current_episode_reward = 0.0
    finally:
        env.close()
    metadata["elapsed_seconds"] = time.monotonic() - started
    (output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Selected checkpoint: {output / 'best.pt'}; validation score {best_score:.3f}", flush=True)
    return output / "best.pt"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--teacher-games", type=int, default=600)
    parser.add_argument("--imitation-epochs", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--rollout-steps", type=int, default=2048)
    parser.add_argument("--validation-every", type=int, default=20)
    parser.add_argument("--validation-pairs", type=int, default=2)
    parser.add_argument("--warm-start", type=Path)
    args = parser.parse_args()
    train(**vars(args))


if __name__ == "__main__":
    main()
