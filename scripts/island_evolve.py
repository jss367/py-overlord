"""Island-model evolution for the Lisbon board.

Runs one ``GeneticTrainer`` per seed strategy. Each trainer uses identical
hyperparameters and the same fixed opponent panel, so fitness numbers are
comparable across islands. The champions are saved as importable Python
files for the tournament stage.

The whole point of the island model is to escape local optima: each seed
represents a distinct theory of the kingdom (Investment Rush, WV/Peddler
Engine, Watchtower Topdeck, Festival BigMoney, Gardens Slog, City Pile
Engine). After every island has had equal optimization budget against a
neutral panel, the champions face each other in
``scripts/island_tournament.py``.

Usage
-----
    # Smoke test (sequential, small budget):
    python scripts/island_evolve.py --smoke

    # Real run, parallel across islands:
    python scripts/island_evolve.py \
        --population 30 --generations 60 --games-per-eval 30 --parallel

    # Single island for debugging:
    python scripts/island_evolve.py --only "Lisbon Investment Rush"
"""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import coloredlogs

from dominion.boards.loader import load_board
from dominion.runner import save_strategy_as_python
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.strategy_loader import StrategyLoader


# Seeds the islands start from. Each is a distinct theory of the kingdom.
# Order matters only for log readability — every island gets the same panel
# and the same budget regardless of position in this list.
LISBON_SEEDS = [
    "Lisbon Investment Rush",
    "Lisbon WV Peddler Engine",
    "Lisbon Watchtower Topdeck",
    "Lisbon Festival BigMoney",
    "Lisbon Gardens Slog",
    "Lisbon City Engine",
]

# Fixed panel for every island. Big Money is the non-negotiable speed-test
# (a deck that builds slowly should win less vs BM than a deck that builds
# fast — that's the signal previous panels filtered out). ClerkCollection-
# Colony is the existing engine baseline. Neither is one of the seeds.
LISBON_PANEL = [
    "Big Money",
    "ClerkCollectionColony",
]


logger = logging.getLogger(__name__)


@dataclass
class IslandResult:
    seed_name: str
    output_path: str
    fitness: float
    win_rate_vs_panel: float
    panel_breakdown: list[tuple]
    wall_seconds: float


def _safe_class_name(name: str) -> str:
    return "".join(ch for ch in name.title() if ch.isalnum()) + "Champion"


def _safe_filename(name: str) -> str:
    slug = name.lower().replace(" ", "_").replace("'", "")
    return "".join(ch for ch in slug if ch.isalnum() or ch in ("_",))


def run_one_island(
    seed_name: str,
    board_path: str,
    panel_names: list[str],
    population: int,
    generations: int,
    games_per_eval: int,
    mutation_rate: float,
    output_dir: str,
    run_id: str,
) -> IslandResult:
    """Run a single island. Designed to be called in a subprocess: takes only
    picklable arguments and constructs the trainer + loader inside."""

    # Configure logging in the subprocess. Each island prefixes its logs with
    # its seed name so a parallel run is still readable.
    coloredlogs.install(
        level="INFO",
        logger=logging.getLogger(),
        fmt=f"%(asctime)s [{seed_name}] %(message)s",
    )

    loader = StrategyLoader()
    seed = loader.get_strategy(seed_name)
    if seed is None:
        raise ValueError(f"Seed strategy not found: {seed_name!r}")

    panel = []
    for name in panel_names:
        opp = loader.get_strategy(name)
        if opp is None:
            raise ValueError(f"Panel strategy not found: {name!r}")
        panel.append(opp)

    board_config = load_board(board_path)

    trainer = GeneticTrainer(
        kingdom_cards=board_config.kingdom_cards,
        population_size=population,
        generations=generations,
        mutation_rate=mutation_rate,
        games_per_eval=games_per_eval,
        board_config=board_config,
        log_folder=f"island_logs/{run_id}/{_safe_filename(seed_name)}",
    )
    trainer.inject_strategy(seed)
    trainer.set_baseline_panel(panel)

    start = time.monotonic()
    best, metrics = trainer.train()
    elapsed = time.monotonic() - start

    if best is None:
        raise RuntimeError(f"Island {seed_name} produced no champion")

    # Replace the GA's auto-generated internal name (e.g. "gen3-4773797616")
    # with something readable so the tournament report identifies champions by
    # their archetype rather than a memory address.
    best.name = f"{seed_name} Champion"

    output_path = Path(output_dir) / f"{_safe_filename(seed_name)}_champion.py"
    save_strategy_as_python(best, output_path, _safe_class_name(seed_name))
    logger.info(
        "Island done: %s  fitness=%.2f  win_rate=%.1f%%  saved=%s",
        seed_name,
        metrics.get("fitness", 0.0),
        metrics.get("win_rate", 0.0),
        output_path,
    )

    return IslandResult(
        seed_name=seed_name,
        output_path=str(output_path),
        fitness=float(metrics.get("fitness", 0.0)),
        win_rate_vs_panel=float(metrics.get("win_rate", 0.0)),
        panel_breakdown=list(trainer.last_eval_breakdown),
        wall_seconds=elapsed,
    )


def main() -> None:
    coloredlogs.install(level="INFO", logger=logging.getLogger())

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", default="boards/lisbon.txt")
    parser.add_argument("--population", type=int, default=30)
    parser.add_argument("--generations", type=int, default=60)
    parser.add_argument("--games-per-eval", type=int, default=30)
    parser.add_argument("--mutation-rate", type=float, default=0.15)
    parser.add_argument(
        "--output-dir",
        default="generated_strategies/island_champions",
        help="Where to save each island's champion as a Python file.",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        default=LISBON_SEEDS,
        help="Seed strategy names. Defaults to the six Lisbon island seeds.",
    )
    parser.add_argument(
        "--only",
        help="Run only this seed (for debugging one island in isolation).",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run islands in parallel using multiprocessing.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=0,
        help="Cap parallel workers. 0 = number of seeds (one worker per island).",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Override hyperparameters for a fast smoke test.",
    )
    args = parser.parse_args()

    if args.smoke:
        args.population = 12
        args.generations = 5
        args.games_per_eval = 8

    seeds = [args.only] if args.only else list(args.seeds)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Run id: %s", run_id)
    logger.info("Seeds: %s", seeds)
    logger.info("Panel: %s", LISBON_PANEL)
    logger.info(
        "Hyperparameters: pop=%d gens=%d games=%d mut=%.2f parallel=%s",
        args.population, args.generations, args.games_per_eval, args.mutation_rate, args.parallel,
    )

    kwargs = dict(
        board_path=args.board,
        panel_names=LISBON_PANEL,
        population=args.population,
        generations=args.generations,
        games_per_eval=args.games_per_eval,
        mutation_rate=args.mutation_rate,
        output_dir=str(output_dir),
        run_id=run_id,
    )

    results: list[IslandResult] = []
    # Track failures so a partial run can't silently produce a manifest the
    # downstream tournament would treat as complete. The whole point of the
    # island model is that every seed gets the same budget — if one island
    # crashed mid-evolution, comparing the rest is meaningless.
    failed_seeds: list[str] = []

    if args.parallel and len(seeds) > 1:
        max_workers = args.max_workers or len(seeds)
        # 'spawn' is the safe default — 'fork' on macOS can deadlock with
        # libraries that aren't fork-safe (notably some BLAS / logging stacks).
        ctx = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as ex:
            futures = {
                ex.submit(run_one_island, seed_name=seed, **kwargs): seed
                for seed in seeds
            }
            for fut in as_completed(futures):
                seed = futures[fut]
                try:
                    results.append(fut.result())
                except Exception:
                    logger.exception("Island %s failed", seed)
                    failed_seeds.append(seed)
    else:
        for seed in seeds:
            try:
                results.append(run_one_island(seed_name=seed, **kwargs))
            except Exception:
                logger.exception("Island %s failed", seed)
                failed_seeds.append(seed)

    if failed_seeds:
        logger.error(
            "Run incomplete — %d/%d islands failed: %s. Not writing manifest.",
            len(failed_seeds), len(seeds), failed_seeds,
        )
        sys.exit(1)

    # Persist a manifest so the tournament runner can pick it up automatically.
    manifest = {
        "run_id": run_id,
        "board": args.board,
        "panel": LISBON_PANEL,
        "hyperparameters": {
            "population": args.population,
            "generations": args.generations,
            "games_per_eval": args.games_per_eval,
            "mutation_rate": args.mutation_rate,
        },
        "islands": [asdict(r) for r in results],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Manifest written: %s", manifest_path)

    print("\n=== Island summary ===")
    print(f"{'Seed':<35} {'fitness':>8} {'win%':>7} {'time(s)':>9}")
    for r in sorted(results, key=lambda r: -r.fitness):
        print(f"{r.seed_name:<35} {r.fitness:>8.2f} {r.win_rate_vs_panel:>6.1f}% {r.wall_seconds:>9.1f}")


if __name__ == "__main__":
    main()
