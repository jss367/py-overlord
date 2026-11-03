"""Check that typed policies reproduce the two strong Oslo references."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from dominion.analysis.strategic_genome_audit import audit_equivalence, oslo_reference_genome
from dominion.boards.loader import load_board
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.simulation.reflective_strategy_search import compile_genome, genome_text
from dominion.simulation.structured_genome import KingdomInfo
from dominion.strategy.strategy_loader import StrategyLoader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=25, help="Shuffle seeds per opponent, both seats")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.pairs < 1:
        parser.error("--pairs must be positive")
    if args.output.exists():
        parser.error("--output must be a new directory")
    args.output.mkdir(parents=True)
    board, loader = load_board("boards/oslo.txt"), StrategyLoader()
    info = KingdomInfo.from_kingdom(board.kingdom_cards)
    names = ["Oslo Workers Village Magnate Refined Engine",
             "Oslo Workers Village Magnate Multi Colony Engine"]
    report = {"schema_version": 2, "board": asdict(board), "seed": args.seed,
              "pairs": args.pairs, "simulation_fingerprint": tournament_fingerprint(), "results": {}}
    for index, name in enumerate(names):
        text = genome_text(oslo_reference_genome(multi_colony=bool(index)))
        (args.output / f"reference-{index + 1}.json").write_text(text)
        compiled = compile_genome(text, info)
        opponents = {"Big Money": loader.get_strategy("Big Money"),
                     names[1 - index]: loader.get_strategy(names[1 - index])}
        result = audit_equivalence(board, loader.get_strategy(name), compiled, opponents,
                                   pairs=args.pairs, seed=args.seed, log_dir=args.output / "logs")
        report["results"][name] = {"genome": json.loads(text), **result}
        (args.output / "audit.json").write_text(json.dumps(report, indent=2))
        print(f"{name}: {result['paired_games']} game pairs, "
              f"{result['decisions_compared']} decisions, equivalent={result['equivalent']}", flush=True)
    if not all(result["equivalent"] for result in report["results"].values()):
        raise SystemExit("Reference equivalence failed; inspect audit.json")


if __name__ == "__main__":
    main()
