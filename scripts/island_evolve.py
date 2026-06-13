"""Island-model evolution for any board.

Runs one ``GeneticTrainer`` per island seed. Each trainer uses identical
hyperparameters and the same fixed opponent panel, so runs are comparable
across islands. The champions are saved as importable Python files for the
tournament stage.

The whole point of the island model is to escape local optima: each island
starts from a distinct theory of the kingdom. By default the roster is
**derived from the board** (see :mod:`dominion.analysis.island_seeds`):
compatible strategies from the reuse library, one island per trick-scanner
interaction, a Big Money archetype island, and random structured-menu
islands to fill the roster. ``--seeds`` overrides the roster with explicit
registered strategy names (the original hand-curated workflow).

After every island has had equal optimization budget, the champions face
each other in ``scripts/island_tournament.py`` (and optionally merge in
``scripts/island_merge.py``).

Note on fitness comparability: each island's trainer maintains its own hall
of fame, so late-run fitness numbers are scored partly against the island's
own ancestors. Treat manifest fitness as a within-island signal; the
tournament is the cross-island ranking.

Usage
-----
    # Smoke test (sequential, small budget):
    python scripts/island_evolve.py --board boards/lisbon.txt --smoke

    # Real run, parallel across islands, board-derived roster:
    python scripts/island_evolve.py --board boards/lisbon.txt \
        --population 30 --generations 60 --games-per-eval 30 --parallel

    # Explicit seed roster (original workflow):
    python scripts/island_evolve.py --board boards/lisbon.txt \
        --seeds "Lisbon Investment Rush" "Lisbon City Engine"

    # Single island for debugging:
    python scripts/island_evolve.py --board boards/lisbon.txt --only "Big Money Island"
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

import coloredlogs

from dominion.analysis.island_seeds import (
    IslandSpec,
    derive_island_specs,
    resolve_island_seed,
)
from dominion.boards.loader import load_board
from dominion.runner import save_strategy_as_python
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.strategy_loader import StrategyLoader

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
    spec_kind: str,
    spec_key: str,
    island_name: str,
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
    plain-string arguments and rebuilds the seed strategy + panel inside
    (strategy objects hold lambda conditions and don't survive the spawn
    boundary)."""

    # Configure logging in the subprocess. Each island prefixes its logs with
    # its island name so a parallel run is still readable.
    coloredlogs.install(
        level="INFO",
        logger=logging.getLogger(),
        fmt=f"%(asctime)s [{island_name}] %(message)s",
    )

    board_config = load_board(board_path)
    loader = StrategyLoader()

    spec = IslandSpec(spec_kind, spec_key, island_name)
    seed = resolve_island_seed(spec, board_config, loader)

    panel = []
    for name in panel_names:
        opp = loader.get_strategy(name)
        if opp is None:
            raise ValueError(f"Panel strategy not found: {name!r}")
        panel.append(opp)

    trainer = GeneticTrainer(
        kingdom_cards=board_config.kingdom_cards,
        population_size=population,
        generations=generations,
        mutation_rate=mutation_rate,
        games_per_eval=games_per_eval,
        board_config=board_config,
        log_folder=f"island_logs/{run_id}/{_safe_filename(island_name)}",
    )
    if seed is not None:
        trainer.inject_strategy(seed)
    trainer.set_baseline_panel(panel)

    start = time.monotonic()
    best, metrics = trainer.train()
    elapsed = time.monotonic() - start

    if best is None:
        raise RuntimeError(f"Island {island_name} produced no champion")

    # Replace the GA's auto-generated internal name (e.g. "gen3-4773797616")
    # with something readable so the tournament report identifies champions by
    # their archetype rather than a memory address.
    best.name = f"{island_name} Champion"

    output_path = Path(output_dir) / f"{_safe_filename(island_name)}_champion.py"
    save_strategy_as_python(best, output_path, _safe_class_name(island_name))
    logger.info(
        "Island done: %s  fitness=%.2f  win_rate=%.1f%%  saved=%s",
        island_name,
        metrics.get("fitness", 0.0),
        metrics.get("win_rate", 0.0),
        output_path,
    )

    return IslandResult(
        seed_name=island_name,
        output_path=str(output_path),
        fitness=float(metrics.get("fitness", 0.0)),
        win_rate_vs_panel=float(metrics.get("win_rate", 0.0)),
        # ``best_eval_breakdown`` is the snapshot taken when ``best`` was first
        # selected as the champion. Using ``last_eval_breakdown`` here would
        # publish the breakdown of whichever candidate was evaluated last in
        # the final generation, not the saved champion.
        panel_breakdown=list(trainer.best_eval_breakdown),
        wall_seconds=elapsed,
    )


def _resolve_panel_names(board_config, explicit: list[str] | None) -> list[str]:
    """Resolve the opponent panel names shared by every island.

    With ``--panel``, the user's names are used verbatim (they must resolve
    via StrategyLoader, both here and later in island_merge). Otherwise the
    default is the built-in baseline panel compatible with this kingdom —
    deterministic for a given board, so every island sees the same panel.
    """
    if explicit:
        return list(explicit)

    probe = GeneticTrainer(
        kingdom_cards=board_config.kingdom_cards,
        population_size=1,
        generations=1,
        board_config=board_config,
        log_folder="island_logs/_panel_probe",
    )
    panel = probe.build_default_baseline_panel()
    loader = StrategyLoader()
    names = []
    for strategy in panel:
        # Manifest panel names must round-trip through StrategyLoader (the
        # merge stage re-resolves them), so verify before recording.
        if loader.get_strategy(strategy.name) is not None:
            names.append(strategy.name)
    return names or ["Big Money"]


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
        default=None,
        help="Explicit seed strategy names (registered in the StrategyLoader). "
        "Default: derive the island roster from the board (library reuse + "
        "trick scanner + Big Money + random islands).",
    )
    parser.add_argument(
        "--max-islands",
        type=int,
        default=6,
        help="Roster size when deriving islands from the board (default: 6).",
    )
    parser.add_argument(
        "--panel",
        nargs="+",
        default=None,
        help="Opponent panel strategy names shared by every island. "
        "Default: the built-in baseline panel compatible with this kingdom.",
    )
    parser.add_argument(
        "--only",
        help="Run only the island with this name (for debugging in isolation).",
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
        help="Cap parallel workers. 0 = number of islands (one worker each).",
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

    board_config = load_board(args.board)

    if args.seeds:
        specs = [IslandSpec("loader", name, name) for name in args.seeds]
    else:
        specs = derive_island_specs(board_config, max_islands=args.max_islands)
        logger.info(
            "Derived island roster from board: %s",
            ", ".join(f"{s.name} [{s.kind}]" for s in specs),
        )

    if args.only:
        specs = [s for s in specs if s.name == args.only]
        if not specs:
            logger.error("No island named %r in the roster", args.only)
            sys.exit(1)

    panel_names = _resolve_panel_names(board_config, args.panel)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Run id: %s", run_id)
    logger.info("Islands: %s", [s.name for s in specs])
    logger.info("Panel: %s", panel_names)
    logger.info(
        "Hyperparameters: pop=%d gens=%d games=%d mut=%.2f parallel=%s",
        args.population, args.generations, args.games_per_eval, args.mutation_rate, args.parallel,
    )

    kwargs = dict(
        board_path=args.board,
        panel_names=panel_names,
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
    failed_islands: list[str] = []

    if args.parallel and len(specs) > 1:
        max_workers = args.max_workers or len(specs)
        # 'spawn' is the safe default — 'fork' on macOS can deadlock with
        # libraries that aren't fork-safe (notably some BLAS / logging stacks).
        ctx = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as ex:
            futures = {
                ex.submit(
                    run_one_island,
                    spec_kind=spec.kind,
                    spec_key=spec.key,
                    island_name=spec.name,
                    **kwargs,
                ): spec.name
                for spec in specs
            }
            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    results.append(fut.result())
                except Exception:
                    logger.exception("Island %s failed", name)
                    failed_islands.append(name)
    else:
        for spec in specs:
            try:
                results.append(
                    run_one_island(
                        spec_kind=spec.kind,
                        spec_key=spec.key,
                        island_name=spec.name,
                        **kwargs,
                    )
                )
            except Exception:
                logger.exception("Island %s failed", spec.name)
                failed_islands.append(spec.name)

    if failed_islands:
        logger.error(
            "Run incomplete — %d/%d islands failed: %s. Not writing manifest.",
            len(failed_islands), len(specs), failed_islands,
        )
        sys.exit(1)

    # Persist a manifest so the tournament runner can pick it up automatically.
    manifest = {
        "run_id": run_id,
        "board": args.board,
        "panel": panel_names,
        "islands_specs": [asdict(s) for s in specs],
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
    print(f"{'Island':<35} {'fitness':>8} {'win%':>7} {'time(s)':>9}")
    for r in sorted(results, key=lambda r: -r.fitness):
        print(f"{r.seed_name:<35} {r.fitness:>8.2f} {r.win_rate_vs_panel:>6.1f}% {r.wall_seconds:>9.1f}")


if __name__ == "__main__":
    main()
