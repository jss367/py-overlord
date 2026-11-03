"""Compare frozen Shrine policies directly with the previous Tea House winner.

Independent chunks retain paired score moments, so the merged confidence
interval treats each seat-swapped shuffle seed as one observation.
"""

import argparse
import json
from pathlib import Path

from scripts.search_lucky_coin_cleanup import CHAMPION
from scripts.search_lucky_coin_ruins import run


def aggregate(spec, results):
    rows = [r for r in results if r["a"] == spec]
    games = sum(r["games"] for r in rows)
    pairs = sum(r["seed_pairs"] for r in rows)
    rate = sum(r["rate"] * r["games"] for r in rows) / games
    squares = sum(r["pair_score_sum_squares"] for r in rows)
    se = (
        (max(0, squares - pairs * rate * rate) / (pairs - 1) / pairs) ** 0.5
        if pairs > 1
        else 0
    )
    names = set().union(*(r["deck"] for r in rows))
    return dict(
        params=spec,
        games=games,
        seed_pairs=pairs,
        wins=sum(r["wins"] for r in rows),
        ties=sum(r["ties"] for r in rows),
        rate=rate,
        ci95=[max(0, rate - 1.96 * se), min(1, rate + 1.96 * se)],
        scores=[sum(r["scores"][j] * r["games"] for r in rows) / games for j in [0, 1]],
        deck={
            n: sum(r["deck"].get(n, 0) * r["games"] for r in rows) / games
            for n in sorted(names)
        },
        truncated=sum(r["truncated"] for r in rows),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specs", type=Path, required=True)
    parser.add_argument("--games", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--chunk-games", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.games < 2 or args.games % 2 or args.chunk_games < 2 or args.chunk_games % 2:
        parser.error("--games and --chunk-games must be positive and even")
    specs = json.loads(args.specs.read_text())
    tasks = [
        (a, CHAMPION, min(args.chunk_games, args.games - start), args.seed + start // 2)
        for a in specs
        for start in range(0, args.games, args.chunk_games)
    ]
    raw = args.output.with_name(args.output.stem + "-chunks.json")
    results = run(tasks, raw, args.workers)
    ranked = sorted([aggregate(a, results) for a in specs], key=lambda r: -r["rate"])
    out = dict(
        opponent=CHAMPION,
        seed=args.seed,
        games_per_policy=args.games,
        scoring="Win share for Shrine; ties count half. Paired 95% intervals use one observation per seat-swapped seed.",
        results=ranked,
        chunks=results,
    )
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    for r in ranked:
        print(
            f"{100 * r['rate']:.2f}% [{100 * r['ci95'][0]:.2f}, {100 * r['ci95'][1]:.2f}] {r['params']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
