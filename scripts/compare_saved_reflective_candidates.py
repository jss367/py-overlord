"""Evaluate trusted local reflective-search checkpoints without any model calls.

Candidates stay fixed. This is a diagnostic of saved recommendations, not an
equal-compute comparison of GEPA-only and genetic-search algorithms. Never load
checkpoints from an untrusted source: cloudpickle can execute Python code.
"""

import argparse
from contextlib import ExitStack
from dataclasses import asdict
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import platform
import shlex
from statistics import mean, stdev
import sys

import cloudpickle
from scipy.stats import t

from dominion.analysis.engine_archetypes import build_engine_seeds
from dominion.boards.loader import BoardConfig
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.simulation.adversarial_league import genome_signature
from dominion.simulation.reflective_strategy_search import (
    MatchupCase, MatchupEvaluator, compile_genome, game_seed,
)
from dominion.simulation.structured_genome import KingdomInfo
from dominion.strategy.strategy_loader import StrategyLoader


ARMS = ("proposal", "assisted", "control")
LABELS = {"proposal": "Original GEPA proposal", "assisted": "Final assisted recommendation",
          "control": "Genetic-only control"}
NAMESPACE = int.from_bytes(sha256(b"saved-reflective-candidates-diagnostic-v1").digest()[:8], "big")
GAME_COLUMNS = ("seed", "seat", "won", "score", "opponent_score", "turns",
                "win_share", "result", "termination_reason")


def fresh_cases(opponents, seed, games, *, direct=False):
    if type(games) is not int or games < 2 or games % 2:
        raise ValueError("Games must be positive, complete seat pairs")
    return [MatchupCase(name, game_seed(NAMESPACE, seed, int(direct), i), games, "diagnostic")
            for i, name in enumerate(opponents)]


def case_seeds(cases):
    return {game_seed(case.seed, pair) for case in cases for pair in range(case.games // 2)}


def recorded_seeds(value):
    """Collect shuffle seeds from all saved source game records, not case IDs."""
    found = set()
    if isinstance(value, dict):
        games = value.get("games")
        if isinstance(games, list):
            found.update(row["seed"] for row in games if isinstance(row, dict) and "seat" in row)
        for child in value.values():
            if isinstance(child, (dict, list)):
                found.update(recorded_seeds(child))
    elif isinstance(value, list):
        for child in value:
            found.update(recorded_seeds(child))
    return found


def interval(values):
    values = list(values)
    if len(values) < 2:
        raise ValueError("At least two independent search seeds are required")
    center = mean(values)
    radius = float(t.ppf(0.975, len(values) - 1)) * stdev(values) / len(values)**0.5
    return {"mean": center, "ci95": [center - radius, center + radius], "seed_values": values}


def panel_mean(panel):
    return mean(matchup["win_rate"] for matchup in panel["matchups"])


def analyze(results):
    comparisons = {}
    for left, right in (("assisted", "proposal"), ("proposal", "control"), ("assisted", "control")):
        comparisons[f"{left}_minus_{right}"] = interval(
            panel_mean(r["panels"][r["aliases"][left]]) - panel_mean(r["panels"][r["aliases"][right]])
            for r in results
        )
    return {"panel_differences": comparisons,
            "panel_means": {arm: mean(panel_mean(r["panels"][r["aliases"][arm]]) for r in results)
                            for arm in ARMS},
            "unchanged_proposals": sum(r["aliases"]["proposal"] == r["aliases"]["assisted"] for r in results),
            "total_simulated_games": sum(r["simulated_games"] for r in results)}


def compact_matchup(matchup):
    return {**matchup, "games": {"columns": GAME_COLUMNS,
                                 "rows": [[row[key] for key in GAME_COLUMNS] for row in
                                          sorted(matchup["games"], key=lambda row: (row["seed"], row["seat"]))]}}


def run_comparison(source, output, *, games=1000, workers=1):
    if output.exists():
        raise ValueError("Output must be a new directory")
    source_manifest = json.loads((source / "experiment.json").read_text())
    if source_manifest.get("status") != "complete":
        raise ValueError("Source experiment must be complete")
    fingerprint = tournament_fingerprint()
    if source_manifest["simulation_fingerprint"] != fingerprint:
        raise ValueError("Simulator inputs differ from the source experiment")
    seeds = source_manifest["settings"]["seeds"]
    if len(seeds) < 2 or len(set(seeds)) != len(seeds):
        raise ValueError("At least two distinct source search seeds are required")
    board = BoardConfig(**source_manifest["board"])
    loader = StrategyLoader()
    engines = dict(build_engine_seeds(board, max_engines=2))
    opponents = {name: engines[name] if name in engines else loader.get_strategy(name)
                 for name in source_manifest["opponents"]}
    if any(strategy is None for strategy in opponents.values()):
        raise ValueError("A source opponent cannot be reconstructed")
    info = KingdomInfo.from_kingdom(board.kingdom_cards)
    locked, hashes, old_seeds = {}, {}, set()
    # Load and freeze EVERY candidate before observing ANY new game outcomes.
    for seed in seeds:
        folder = source / f"seed-{seed}"
        files = {name: (folder / name).read_bytes() for name in
                 ("selected-genome.json", "genetic-strategy.pkl", "gepa_genetic-strategy.pkl")}
        hashes[str(seed)] = {name: sha256(data).hexdigest() for name, data in files.items()}
        strategies = {"proposal": compile_genome(files["selected-genome.json"].decode(), info, "GEPA proposed seed"),
                      "assisted": cloudpickle.loads(files["gepa_genetic-strategy.pkl"]),
                      "control": cloudpickle.loads(files["genetic-strategy.pkl"])}
        # Type plus compiled policy signature; names do not affect gameplay.
        unique, aliases = {}, {}
        for arm, strategy in strategies.items():
            signature = (type(strategy), genome_signature(strategy))
            same = next((other for other, candidate in unique.items()
                         if (type(candidate), genome_signature(candidate)) == signature), None)
            aliases[arm] = same or arm
            if same is None:
                unique[arm] = strategy
        locked[seed] = (unique, aliases)
        for name in ("evaluation-records.json", "summary.json", "genetic-selection.json", "gepa_genetic-selection.json"):
            old_seeds.update(recorded_seeds(json.loads((folder / name).read_text())))
    all_new = set()
    for seed in seeds:
        panel = case_seeds(fresh_cases(opponents, seed, games))
        direct = case_seeds(fresh_cases(["Opponent"], seed, games, direct=True))
        if panel & direct or all_new & (panel | direct) or old_seeds & (panel | direct):
            raise ValueError("Fresh shuffle seeds overlap another block or saved source games")
        all_new.update(panel | direct)
    output.mkdir(parents=True)
    (output / "runner.py").write_bytes(Path(__file__).read_bytes())
    for seed, (strategies, _) in locked.items():
        folder = output / f"seed-{seed}"
        folder.mkdir()
        for arm, strategy in strategies.items():
            (folder / f"{arm}.pkl").write_bytes(cloudpickle.dumps(strategy))
    (output / "opponents.pkl").write_bytes(cloudpickle.dumps(opponents))
    manifest = {
        "status": "running", "command": shlex.join([sys.executable, *sys.argv]),
        "source": str(source), "source_manifest_sha256": sha256((source / "experiment.json").read_bytes()).hexdigest(),
        "source_checkpoint_sha256": hashes, "simulation_fingerprint": fingerprint,
        "runner_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "python": platform.python_version(),
        "board": asdict(board), "opponents": list(opponents), "search_seeds": seeds,
        "games_per_matchup": games, "workers": workers, "seed_namespace": NAMESPACE,
        "scoring_version": "explicit_outcomes_v1",
        "scoring": "Half credit for natural ties; zero credit for truncated games; explicit outcome counts",
        "freshness_check": {"recorded_source_shuffle_seeds": len(old_seeds), "new_shuffle_seeds": len(all_new),
                            "overlap": 0, "scope": "All saved reflection, selection and held-out game records; unsaved genetic training games cannot be enumerated"},
        "analysis_plan": {
            "primary": "Seed-level paired difference in ordinary opponent-panel mean: final assisted minus original proposal",
            "uncertainty": "Two-sided 95% Student-t interval over search seeds, including zero differences for identical policies",
            "secondary": "Each candidate versus genetic control on the panel; direct pairwise games are descriptive",
            "selection": "All saved candidates locked before new games; no reselection or tuning",
            "limits": "One kingdom and five previously inspected search runs; post-hoc diagnostic, not a new equal-compute algorithm comparison or proof of descent from a proposal",
        },
        "results": [],
    }
    path = output / "comparison.json"
    path.write_text(json.dumps(manifest, indent=2))
    try:
        for seed, (strategies, aliases) in locked.items():
            print(f"Seed {seed}: evaluating {len(strategies)} distinct locked policies", flush=True)
            with ExitStack() as resources:
                evaluator = MatchupEvaluator(board, opponents, output / f"seed-{seed}/panel", workers=workers)
                resources.callback(evaluator.close)
                panels = {arm: evaluator.panel(strategy, fresh_cases(opponents, seed, games))
                          for arm, strategy in strategies.items()}
                direct_results, direct_games = {}, 0
                for left, right in combinations(strategies, 2):
                    direct = MatchupEvaluator(board, {"Opponent": strategies[right]},
                                             output / f"seed-{seed}/{left}-vs-{right}", workers=workers)
                    resources.callback(direct.close)
                    case = fresh_cases(direct.opponents, seed, games, direct=True)[0]
                    direct_results[f"{left}_vs_{right}"] = direct.evaluate(strategies[left], case)
                    direct_games += direct.simulated_games
                    direct.close()
                row = {"seed": seed, "aliases": aliases,
                       "selected_names": {arm: s.name for arm, s in strategies.items()},
                       "panels": {arm: {**panel, "matchups": [compact_matchup(m) for m in panel["matchups"]]}
                                  for arm, panel in panels.items()},
                       "direct": {key: compact_matchup(m) for key, m in direct_results.items()},
                       "simulated_games": evaluator.simulated_games + direct_games}
                manifest["results"].append(row)
                path.write_text(json.dumps(manifest, separators=(",", ":")))
                print(f"Seed {seed}: complete ({row['simulated_games']} games)", flush=True)
        if tournament_fingerprint() != fingerprint:
            raise RuntimeError("Simulator inputs changed during evaluation")
        manifest["analysis"] = analyze(manifest["results"])
        manifest["status"] = "complete"
    except Exception as exc:
        manifest.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        path.write_text(json.dumps(manifest, separators=(",", ":")) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Trusted local completed experiment with pickle checkpoints")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--games", type=int, default=1000, help="Games per opponent and distinct pair; complete seat pairs")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.games < 2 or args.games % 2 or args.workers < 1:
        parser.error("Use a positive even --games and positive --workers")
    result = run_comparison(args.source, args.output, games=args.games, workers=args.workers)
    print(json.dumps(result["analysis"], indent=2))


if __name__ == "__main__":
    main()
