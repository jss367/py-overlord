"""Reproduce the September 2026 retirement screen and held-out comparisons.

Run from the repository root with PYTHONPATH=.; results are resumable JSON.
Archived factories remain explicitly addressable through StrategyLoader.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

from dominion.boards.loader import BoardConfig, load_board
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.reporting.tournament_state import tournament_fingerprint
from compare_all_strategies import _missing_board_components


def source_provenance():
    """Identify the checkout, runtime, and actual simulation inputs, including edits."""
    digest = hashlib.sha256(tournament_fingerprint().encode())
    digest.update(Path(__file__).read_bytes())
    return {
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python_version": sys.version.split()[0],
        "source_fingerprint": digest.hexdigest(),
    }


def validate_provenance(saved, current, label):
    for field in ("source_revision", "python_version", "source_fingerprint"):
        if saved.get(field) != current[field]:
            raise ValueError(
                f"{label}: {field} is missing or differs from the current experiment; "
                "use fresh output paths and rerun both stages from the same source and Python version"
            )


def save_report(path, report, provenance):
    # Detect edits during a pairing as well as changes between invocations.
    validate_provenance(provenance, source_provenance(), "Source changed during evaluation")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(path)


def cohorts():
    custom = BoardConfig(
        kingdom_cards=["Collection", "Emporium", "Forager", "Miser", "Modify",
                       "Patrician", "Rats", "Rebuild", "Skulk", "Snowy Village"],
        events=["Looting"], projects=["Sewers"],
    )
    base = BoardConfig(kingdom_cards=[
        "Chapel", "Festival", "Laboratory", "Market", "Mine", "Moat",
        "Smithy", "Village", "Witch", "Workshop",
    ])
    return [
        ("Torturer and Inn", load_board("boards/torture_campaign.txt"), False,
         [f"Torture Campaign V{v}" for v in (3, 4, 5, 6, 22, 24, 26, 27)],
         "Torture Campaign V25", ["Big Money", "Strategy20260212 111527", "Torture Campaign V27"]),
        *[("Patrician and Collection" + (" with Shelters" if shelters else ""),
           custom, shelters, ["Custom Board Strategy2", "Custom Board Strategy4"],
           "Custom Board Strategy3", ["Big Money", "Custom Board Strategy"])
          for shelters in (False, True)],
        ("Village and Smithy", base, False, ["Strategy20250615 102030"],
         "Chapel Witch", ["Big Money Smithy", "Village Smithy Lab"]),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["screen", "validate"], required=True)
    parser.add_argument("--screen", type=Path, help="Screen JSON used to select validation candidates")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cohort", choices=[c[0] for c in cohorts()], help="Evaluate one board family only")
    args = parser.parse_args()
    if args.stage == "validate" and not args.screen:
        parser.error("--stage validate requires --screen")
    if args.stage == "screen" and args.screen:
        parser.error("--screen is only valid with --stage validate")
    if args.workers < 2:
        parser.error("Use at least two workers for reproducible per-game seeding")
    games = 200 if args.stage == "screen" else 1000
    screen = json.loads(args.screen.read_text()) if args.screen else None
    if screen and (screen["stage"] != "screen" or screen["games_per_pairing"] != 200):
        parser.error("--screen must contain the 200-game screening results")
    provenance = source_provenance()
    if screen:
        try:
            validate_provenance(screen, provenance, "Screening results")
        except ValueError as error:
            parser.error(str(error))
    report = {
        "stage": args.stage, "games_per_pairing": games,
        **provenance, "results": [],
    }
    if args.output.exists():
        saved = json.loads(args.output.read_text())
        try:
            validate_provenance(saved, provenance, "Saved output")
        except ValueError as error:
            parser.error(str(error))
        report.update(saved)
        if report["stage"] != args.stage or report["games_per_pairing"] != games:
            parser.error("Existing output belongs to a different stage")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for label, board, shelters, candidates, replacement, panel in cohorts():
        if args.cohort and label != args.cohort:
            continue
        if screen:
            candidates = [c for c in candidates if any(
                r["cohort"] == label and r["candidate"] == c and r["win_rate"] < .4
                for r in screen["results"]
            )]
        pairings = [(c, replacement) for c in candidates]
        if screen and candidates:
            pairings += [(c, p) for c in [*candidates, replacement] for p in panel]
        with StrategyBattle(board_config=board, use_shelters=shelters,
                            log_frequency=0, workers=args.workers) as battle:
            for candidate, opponent in pairings:
                key = [args.stage, label, candidate, opponent]
                if any(r["key"] == key for r in report["results"]):
                    continue
                for name in (candidate, opponent):
                    strategy = battle.strategy_loader.get_strategy(name)
                    if strategy is None:
                        raise ValueError(f"Unknown strategy: {name}")
                    refs = battle._split_board_references(battle._extract_cards_from_strategy(strategy))
                    missing = _missing_board_components(refs, board, set(board.kingdom_cards))
                    if missing:
                        raise ValueError(f"{name} incompatible with {label}: {missing}")
                seed = int.from_bytes(hashlib.sha256(json.dumps(key).encode()).digest()[:8])
                random.seed(seed)
                result = battle.run_battle(candidate, opponent, games)
                row = {
                    "key": key, "cohort": label, "candidate": candidate, "opponent": opponent,
                    "seed": seed, "board": asdict(board), "use_shelters": shelters,
                    "games": games, "wins": result["strategy1_wins"],
                    "win_rate": result["strategy1_wins"] / games,
                }
                report["results"].append(row)
                save_report(args.output, report, provenance)
                print(f"{label}: {candidate} vs {opponent}: {row['wins']}/{games}", flush=True)
    save_report(args.output, report, provenance)


if __name__ == "__main__":
    main()
