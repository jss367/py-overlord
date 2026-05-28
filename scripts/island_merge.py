"""Merged-final-stage runner: take all island champions, seed them into one
population, evolve a final stage to find hybrid strategies.

Rationale
---------
After ``island_evolve.py``, each archetype has had equal optimization
budget against a fixed panel. The tournament tells you which archetype
won, but pure archetypes may still be sub-optimal compared to *hybrids*
(e.g. a Workers'-Village engine that pivots to Expand-Colony late, or
an Investment rush that opens with two Watchtowers). The merged stage
seeds one population with every champion, evolves for N generations,
and lets crossover/mutation discover those hybrids.

Crucially, this stage uses the *same fixed panel* as the islands — so
fitness numbers here are directly comparable to fitness on each island.
A merged champion that scores higher than every island champion against
the same panel is the genuinely better strategy.

Usage
-----
    python scripts/island_merge.py \
        --manifest generated_strategies/island_champions/<RUN_ID>/manifest.json \
        --generations 30 --population 40 --games-per-eval 30
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import logging
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import coloredlogs

from dominion.boards.loader import load_board
from dominion.runner import save_strategy_as_python
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategy_loader import StrategyLoader


logger = logging.getLogger(__name__)


def _load_strategy_from_path(path: Path) -> EnhancedStrategy:
    spec = importlib.util.spec_from_file_location(f"champion_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ != module.__name__:
            continue
        if issubclass(obj, EnhancedStrategy) and obj is not EnhancedStrategy:
            return obj()
    raise RuntimeError(f"No EnhancedStrategy subclass found in {path}")


def main() -> None:
    coloredlogs.install(level="INFO", logger=logging.getLogger())

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to island_evolve manifest.json.")
    parser.add_argument("--population", type=int, default=40)
    parser.add_argument("--generations", type=int, default=30)
    parser.add_argument("--games-per-eval", type=int, default=30)
    parser.add_argument("--mutation-rate", type=float, default=0.15)
    parser.add_argument(
        "--output-dir",
        default="generated_strategies/island_merged",
    )
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    panel_names = manifest["panel"]
    board_path = manifest["board"]

    loader = StrategyLoader()

    panel = []
    for name in panel_names:
        s = loader.get_strategy(name)
        if s is None:
            raise ValueError(f"Panel strategy not found: {name!r}")
        panel.append(s)
    logger.info("Panel: %s", [s.name for s in panel])

    champions: list[EnhancedStrategy] = []
    for island in manifest["islands"]:
        path = Path(island["output_path"])
        champ = _load_strategy_from_path(path)
        champions.append(champ)
        logger.info("Loaded champion: %s (from %s)", champ.name, path.name)

    if not champions:
        raise ValueError(
            "No champions found in manifest; cannot run merged stage. "
            "Re-run island_evolve.py first."
        )

    board_config = load_board(board_path)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    trainer = GeneticTrainer(
        kingdom_cards=board_config.kingdom_cards,
        population_size=args.population,
        generations=args.generations,
        mutation_rate=args.mutation_rate,
        games_per_eval=args.games_per_eval,
        board_config=board_config,
        log_folder=f"island_logs/{run_id}/merged",
    )
    trainer.inject_strategies(champions)
    trainer.set_baseline_panel(panel)

    start = time.monotonic()
    best, metrics = trainer.train()
    elapsed = time.monotonic() - start

    if best is None:
        raise RuntimeError(
            "Merged stage produced no champion (GeneticTrainer.train() returned None). "
            "Re-run with verbose logging to find the underlying training failure."
        )

    # If the hybrid stage doesn't improve on the injected champions, ``best``
    # is a deepcopy of one of them with its original ``name`` preserved (see
    # GeneticTrainer._inject_strategies). Saving as-is would emit a file
    # whose ``self.name`` collides with the matching island champion, and
    # ``island_tournament.py`` then rejects the entrant list via its
    # duplicate-name guard. Match island_evolve.py and assign a stable
    # merged-stage display name before serialization.
    best.name = "Lisbon Merged Champion"

    output_path = output_dir / "merged_champion.py"
    save_strategy_as_python(best, output_path, "LisbonMergedChampion")
    logger.info(
        "Merged champion fitness=%.2f win_rate=%.1f%% saved=%s (%.1fs)",
        metrics.get("fitness", 0.0),
        metrics.get("win_rate", 0.0),
        output_path,
        elapsed,
    )

    summary = {
        "run_id": run_id,
        "source_manifest": str(args.manifest),
        "board": board_path,
        "panel": panel_names,
        "hyperparameters": {
            "population": args.population,
            "generations": args.generations,
            "games_per_eval": args.games_per_eval,
            "mutation_rate": args.mutation_rate,
        },
        "champion": {
            "output_path": str(output_path),
            "fitness": float(metrics.get("fitness", 0.0)),
            "win_rate_vs_panel": float(metrics.get("win_rate", 0.0)),
            "panel_breakdown": list(trainer.last_eval_breakdown),
            "wall_seconds": elapsed,
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
