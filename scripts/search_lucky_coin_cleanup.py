"""Audit cleanup play against the frozen Tea House policy and a Spice Merchant engine."""

import argparse
import json
from pathlib import Path

from scripts.search_lucky_coin_ruins import run

CHAMPION = dict(
    opening="Tea House",
    shrine=0,
    spice=0,
    lost=0,
    highway=1,
    green=1,
    double="adaptive",
    daimyo=2,
)
SPICE = dict(
    opening="Spice Merchant",
    shrine=0,
    spice=1,
    lost=1,
    highway=2,
    green=1,
    double="adaptive",
    daimyo=2,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["screen", "validate", "matched"])
    parser.add_argument("--specs", type=Path, required=True)
    parser.add_argument("--games", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.games < 2 or args.games % 2:
        parser.error("--games must be positive and even")
    specs = json.loads(args.specs.read_text())
    if args.mode == "screen":
        tasks = [
            (a, b, args.games, args.seed + 2000 * j)
            for a in specs
            for j, b in enumerate([CHAMPION, SPICE])
        ]
    elif args.mode == "matched":
        # Keep all previous cleanup decisions and vary only the new
        # Treasure-management flags.
        tasks = []
        for i, a in enumerate(specs):
            old = dict(
                a,
                cleanup={
                    k: v
                    for k, v in a["cleanup"].items()
                    if k not in ("hold_copper", "mining_first")
                },
            )
            tasks.append((a, old, args.games, args.seed + 2000 * i))
    else:
        # Every finalist faces the frozen recommendation and its own original
        # policy: this separates better cleanup decisions from deck construction.
        tasks = []
        for i, a in enumerate(specs):
            old = {k: v for k, v in a.items() if k != "cleanup"}
            for j, b in enumerate([CHAMPION, SPICE, old]):
                tasks.append((a, b, args.games, args.seed + 10000 * i + 2000 * j))
    results = run(tasks, args.output, args.workers)
    for a in specs:
        rs = [r for r in results if r["a"] == a]
        print(f"{sum(r['rate'] for r in rs) / len(rs):.4f} {a}", flush=True)


if __name__ == "__main__":
    main()
