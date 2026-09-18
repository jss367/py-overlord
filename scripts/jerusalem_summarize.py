"""Trim a Jerusalem search record to the committed summary form.

The raw records carry a per-match deck census that is useful while tuning and
far too large to commit. This keeps the ranking, the per-match outcomes, and
the aggregate counters.
"""

import argparse
import json
from pathlib import Path


DESCRIPTIONS = {
    "search": "Broad screen: each candidate plays the fixed four-policy panel.",
    "refine": "One-field sweeps around the broad screen's leaders.",
    "tournament": "Full round robin among finalists and the archetype panel.",
    "validate": "Held-out games: the winner against fresh seeds and opponents.",
    "ablate": "One-field ablations of the winner, isolating each pile.",
}


def summarize(record, top):
    ranking = [
        {"rate": round(row["rate"], 4), "games": row["games"], "params": row["spec"]}
        for row in record["ranking"][:top]
    ]
    matches = [
        {
            "rate": round(r["rate"], 4),
            "games": r["games"],
            "seed": r["seed"],
            "wins": r["wins"],
            "ties": r["ties"],
            "mean_turns_per_player": round(r["mean_turns_per_player"], 2),
            "points": [round(x, 2) for x in r["points"]],
            "endings": r["endings"],
            "truncated": r["truncated"],
            "a": r["a"],
            "b": r["b"],
        }
        for r in record["results"]
    ]
    return {
        "description": DESCRIPTIONS.get(record["mode"], record["mode"]),
        "mode": record["mode"],
        "board": record["board"],
        "matches": len(record["results"]),
        "games": record["games"],
        "truncated": record["truncated"],
        "elapsed_seconds": round(record["elapsed_seconds"], 1),
        "ranking": ranking,
        "results": matches,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--no-results", action="store_true")
    args = parser.parse_args()
    summary = summarize(json.loads(args.source.read_text()), args.top)
    if args.no_results:
        summary.pop("results")
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"{args.destination}: {args.destination.stat().st_size / 1024:.0f} KiB")


if __name__ == "__main__":
    main()
