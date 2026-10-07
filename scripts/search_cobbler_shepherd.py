"""Focused Cobbler/Shepherd search, with held-out seat-balanced validation."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import random
import time

from dominion.strategy.strategies.shepherd_tragic_hero import ShepherdTragicHero
from scripts.search_shepherd_tragic_hero import MONEY, match as base_match


BASELINE = dict(shepherd=1, hero=1, monastery=0, silver=99, estate=3)


def match(task):
    return base_match(task, strategy_type=ShepherdTragicHero)


def candidates():
    variants = [dict(BASELINE, cobbler=1)]  # Original generic Cobbler control.
    for target, priority, cobblers, adaptive in itertools.product(
        [1, 2, 3, 4, 6, 10], ["draw", "night"], [1, 2], [False, True]
    ):
        variants.append(
            dict(
                BASELINE,
                cobbler=cobblers,
                cobbler_shepherds=target,
                priority=priority,
                cobbler_adaptive=adaptive,
            )
        )
    rng = random.Random(7102026)
    for _ in range(72):
        variants.append(
            dict(
                BASELINE,
                shepherd=rng.choice([0, 1]),
                hero=rng.choice([0, 1, 1, 2]),
                cobbler=rng.choice([1, 1, 2]),
                cobbler_shepherds=rng.choice([2, 3, 4, 6]),
                cobbler_estates=rng.choice([0, 5, 7]),
                cobbler_silver=rng.choice([0, 1, 2]),
                cobbler_adaptive=rng.choice([False, True]),
                priority=rng.choice(["draw", "night", "money"]),
                opening=rng.choice(["Shepherd", "Silver", "Tragic Hero"]),
                monastery=rng.choice([0, 0, 1]),
                monastery_timing="spare",
                estate=rng.choice([1, 2, 3, 4]),
            )
        )
    return list({json.dumps(p, sort_keys=True): p for p in variants}.values())


def run(tasks, output, workers):
    start = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(match, tasks):
            results.append(result)
            if len(results) % 10 == 0 or len(tasks) <= 12:
                print(
                    f"{len(results)}/{len(tasks)} matches, {time.monotonic() - start:.1f}s",
                    flush=True,
                )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n")
    print(
        "Games:",
        sum(r["games"] for r in results),
        "Truncated:",
        sum(r["truncated"] for r in results),
    )
    for r in sorted(results, key=lambda r: -r["rate"])[:12]:
        print(json.dumps({k: r[k] for k in ["a", "rate", "interval95", "games"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["screen", "refine", "validate"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.mode == "screen":
        specs, games, seed = candidates(), 120, 110000000
    else:
        previous = sorted(json.loads(args.input.read_text()), key=lambda r: -r["rate"])
        specs = [r["a"] for r in previous[: 12 if args.mode == "refine" else 4]]
        if args.mode == "refine":
            for parent in specs[:3]:
                for key, values in {
                    "cobbler_shepherds": [1, 2, 3, 4, 6],
                    "cobbler_estates": [0, 4, 6, 8],
                    "cobbler_silver": [0, 1, 2],
                    "cobbler_adaptive": [False, True],
                    "cobbler": [1, 2],
                    "shepherd": [0, 1, 2],
                    "hero": [0, 1, 2],
                    "estate": [1, 2, 3, 4],
                    "priority": ["draw", "night", "money"],
                }.items():
                    specs.extend(dict(parent, **{key: value}) for value in values)
            games, seed = 300, 120000000
        else:
            # Prespecified controls, including the user's simplest proposal.
            specs += [
                dict(BASELINE, cobbler=1),
                dict(BASELINE, cobbler=1, cobbler_shepherds=3),
                dict(BASELINE, cobbler=1, cobbler_shepherds=3, priority="night"),
                dict(BASELINE, cobbler=2, cobbler_shepherds=3, priority="night"),
                dict(BASELINE, cobbler=1, cobbler_shepherds=6, priority="night"),
            ]
            games, seed = 2000, 130000000
    specs = list(
        {
            json.dumps(ShepherdTragicHero(**p).params, sort_keys=True): p for p in specs
        }.values()
    )
    tasks = [(p, BASELINE, games, seed + 10000 * i) for i, p in enumerate(specs)]
    if args.mode == "validate":
        # Freeze the refinement winner before looking at validation results.
        champion = previous[0]["a"]
        tasks += [
            (champion, dict(BASELINE, cobbler=1), 2000, 140000000),
            (champion, MONEY, 1000, 140010000),
            (champion, dict(champion, cobbler=0), 2000, 140020000),
        ]
    run(tasks, args.output, args.workers)


if __name__ == "__main__":
    main()
