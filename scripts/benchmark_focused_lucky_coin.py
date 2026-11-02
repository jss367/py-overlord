"""Strict-rule, equally budgeted cleanup-focused planner benchmarks."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import time

from scripts.research_lucky_coin_rollout import play


def game(task):
    matchup, index, seed, config = task
    enabled = (True, True) if matchup == "cross" else (True, False)
    start = time.time()
    result = play(
        seed + index // 2, bool(index % 2), enabled, matchup=matchup, **config
    )
    result["matchup"] = matchup
    result["index"] = index
    result["seconds"] = time.time() - start
    records = result.pop("decisions")
    result["proposals"] = dict(
        Counter(d["kind"] for d in records if d["proposed_choice"] != d["baseline"])
    )
    result["changed_decisions"] = [d for d in records if d["choice"] != d["baseline"]]
    return result


def summarize(rows):
    rows = sorted(rows, key=lambda x: x["index"])
    values = [r["score"] for r in rows]
    pairs = [sum(values[i : i + 2]) / 2 for i in range(0, len(values), 2)]
    rate = sum(values) / len(values)
    se = (
        (sum((v - rate) ** 2 for v in pairs) / (len(pairs) - 1) / len(pairs)) ** 0.5
        if len(pairs) > 1
        else 0
    )
    searched = Counter()
    changed = Counter()
    proposals = Counter()
    for r in rows:
        searched.update(r["search_counts"])
        changed.update(r["changed_counts"])
        proposals.update(r["proposals"])
    return dict(
        games=len(rows),
        first_policy_win_share=rate,
        ci95=[max(0, rate - 1.96 * se), min(1, rate + 1.96 * se)],
        wins=values.count(1),
        ties=values.count(0.5),
        rollouts=sum(r["rollouts"] for r in rows),
        search_counts=dict(searched),
        changed_counts=dict(changed),
        proposals=dict(proposals),
        results=rows,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--config",
        type=Path,
        default=Path(
            "scripts/data/lucky_coin_ruins/cleanup-focused-planner-config.json"
        ),
    )
    p.add_argument("--games", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--matchups", choices=["mirrors", "cross", "all"], default="mirrors")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.games < 2 or args.games % 2 or args.workers < 1:
        p.error("Require an even positive game count and positive workers")
    config = json.loads(args.config.read_text())
    if config["legacy_change_pass"]:
        p.error("This benchmark requires strict Change rules")
    matchups = (
        ["tea-mirror", "shrine-mirror"]
        if args.matchups == "mirrors"
        else ["cross"]
        if args.matchups == "cross"
        else ["tea-mirror", "shrine-mirror", "cross"]
    )
    tasks = [
        (m, i, args.seed + 10000 * j, config)
        for j, m in enumerate(matchups)
        for i in range(args.games)
    ]
    rows = []
    start = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(game, t) for t in tasks]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 4 == 0:
                print(
                    f"{len(rows)}/{len(tasks)} games, {time.time() - start:.1f}s",
                    flush=True,
                )
    out = dict(
        config=config,
        seed=args.seed,
        games_per_matchup=args.games,
        scoring="First policy win share; ties half; paired 95% intervals treat each seat-swapped seed as one observation.",
        matchups={
            m: summarize([r for r in rows if r["matchup"] == m]) for m in matchups
        },
    )
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    for m, r in out["matchups"].items():
        print(m, {k: v for k, v in r.items() if k != "results"}, flush=True)


if __name__ == "__main__":
    main()
