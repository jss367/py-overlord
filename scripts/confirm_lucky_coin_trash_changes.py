"""Independently confirm every adopted trash change from a frozen benchmark."""

import argparse
import json
from pathlib import Path
from statistics import NormalDist

from dominion.ai.lucky_coin_rollout import RolloutController
from scripts.research_lucky_coin_rollout import play


def confirm(benchmark, samples):
    if benchmark["config"].get("legacy_change_pass", False):
        raise ValueError("Trash confirmation requires strict Change rules")
    targets = [
        (matchup, game, decision)
        for matchup, result in benchmark["matchups"].items()
        for game in result["results"]
        for decision in game["changed_decisions"]
        if decision["kind"] == "trash"
    ]
    results = []
    z = NormalDist().inv_cdf(1 - 0.05 / (2 * len(targets))) if targets else None
    for matchup, game, recorded in targets:
        captured = []

        def observer(d):
            if d.kind == "trash" and d.identifier == recorded["identifier"]:
                captured.append(d)

        replay = play(
            game["seed"],
            game["swap"],
            (True, True) if matchup == "cross" else (True, False),
            observer=observer,
            matchup=matchup,
            **benchmark["config"],
        )
        if replay["score"] != game["score"] or len(captured) != 1:
            raise RuntimeError("Frozen benchmark game did not reproduce")
        d = captured[0]
        observation = json.loads(json.dumps(d.observation))
        if observation != recorded["observation"] or d.baseline != recorded["baseline"]:
            raise RuntimeError("Captured trash decision differs from benchmark")
        c = RolloutController(enabled=(False, False))
        base, alternative, diffs = [], [], []
        for j in range(samples):
            seed = c.sample_seed(d, j, salt=4)
            a = c.outcome(d, d.baseline, seed)
            b = c.outcome(d, recorded["choice"], seed)
            base.append(a)
            alternative.append(b)
            diffs.append(b - a)
        mean = sum(diffs) / samples
        se = (sum((v - mean) ** 2 for v in diffs) / (samples - 1) / samples) ** 0.5
        results.append(
            dict(
                matchup=matchup,
                identifier=d.identifier,
                observation=d.observation,
                baseline=d.baseline,
                choice=recorded["choice"],
                samples=samples,
                baseline_win_share=sum(base) / samples,
                alternative_win_share=sum(alternative) / samples,
                delta=mean,
                adjusted_ci95=[mean - z * se, mean + z * se],
                rollouts=c.rollouts,
            )
        )
    return dict(
        selection="Every adopted trash change in the supplied benchmark; no filtering by verification effect size",
        independent_sample_salt=4,
        adjustment="Bonferroni over all adopted trash changes in this benchmark",
        results=results,
        rollouts=sum(r["rollouts"] for r in results),
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--benchmark", type=Path, required=True)
    p.add_argument("--samples", type=int, default=256)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.samples < 2:
        p.error("Require at least two independent samples")
    result = confirm(json.loads(args.benchmark.read_text()), args.samples)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for r in result["results"]:
        print(r["baseline"], r["choice"], r["delta"], r["adjusted_ci95"], flush=True)


if __name__ == "__main__":
    main()
