"""Compare the existing genetic search with an optional GEPA-proposed seed.

Example: PYTHONPATH=. python scripts/reflective_evolve.py --board boards/oslo.txt
    --reflection-backend codex --seeds 1 2 3
    --reference "Oslo Workers Village Magnate Refined Engine"

No library champions are copied into the editable JSON plan. Both genetic arms
receive the same board-derived engines; the treatment adds one GEPA seed. This
can share a hard game allowance with --search-game-budget. Without that flag,
the earlier extra-compute experiment remains available.
"""

import argparse
from copy import deepcopy
from contextlib import ExitStack
from dataclasses import asdict
import importlib.metadata
import json
from pathlib import Path
import random
import shlex
import sys
import time

from dominion.analysis.engine_archetypes import build_engine_seeds
from dominion.boards.loader import load_board
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.simulation.adversarial_league import AdversarialLeague, ORIGIN_SEED, genome_signature
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.simulation_budget import SimulationBudget
from dominion.simulation.reflective_strategy_search import (
    MatchupEvaluator, board_seed, compile_genome, game_seed, genome_text, matchup_cases, optimize_strategy,
)
from dominion.strategy.strategy_loader import StrategyLoader


def genetic_search(board, opponents, initial_seeds, seed, args, output, *,
                   simulation_budget=None, reserve_selection_games=0):
    random.seed(seed)
    league = AdversarialLeague(capacity=len(opponents) + 2)
    # Big Money is the trainer's static panel, so don't duplicate it in the pool.
    for name, strategy in opponents.items():
        if name != "Big Money":
            league.add(strategy, name=name, origin=ORIGIN_SEED)
    trainer = GeneticTrainer(
        board.kingdom_cards, board_config=board, population_size=args.population,
        generations=args.generations, games_per_eval=args.train_games * len(opponents),
        refine_games=args.train_games * len(opponents),
        confirm_games=args.validation_games * len(opponents),
        confirm_min_games_per_opponent=args.validation_games,
        worst_case_weight=0.5, league=league if simulation_budget is None else None,
        eval_seed=seed, workers=args.workers,
        shape_rewards=False, log_folder=str(output / "genetic-logs"),
        genome_schema_version=getattr(args, "genome_schema", 2),
        simulation_budget=simulation_budget, budget_reserve_games=reserve_selection_games,
        hall_of_fame_size=3 if simulation_budget is None else 0,
    )
    if simulation_budget is not None:
        # Fixed reference panels keep the search objectives identical and all
        # per-opponent samples in complete seat pairs throughout both arms.
        trainer.set_baseline_panel(deepcopy(list(opponents.values())))
    trainer.battle_system.logger.log_frequency = 0
    trainer.inject_strategies(deepcopy(initial_seeds))
    started = time.monotonic()
    champion, metadata = trainer.train()
    if champion is None:
        raise RuntimeError(f"Genetic search failed: {metadata}")
    return champion, {**metadata, "elapsed_seconds": time.monotonic() - started}


def distinct_seeds(strategies):
    seen, seeds = set(), []
    for strategy in strategies:
        signature = genome_signature(strategy)
        if signature not in seen:
            seen.add(signature)
            seeds.append(strategy)
    return seeds


def budgeted_selection_cases(opponents, seed, minimum_games, options, remaining):
    """Spend the remainder on equal, complete seat pairs for every option."""
    minimum = options * len(opponents) * minimum_games
    if remaining < minimum:
        raise RuntimeError("Search did not preserve the recommendation-selection reserve")
    block = 2 * options * len(opponents)
    games = minimum_games + 2 * ((remaining - minimum) // block)
    return matchup_cases(opponents, seed, games, "validation")


def run_seed(board, opponents, seed, args, output):
    with ExitStack() as resources:
        return _run_seed(board, opponents, seed, args, output, resources)


def _run_seed(board, opponents, seed, args, output, resources):
    output.mkdir(parents=True)
    editable = (args.seed_genome.read_text() if args.seed_genome
                else genome_text(board_seed(board), getattr(args, "genome_schema", 2)))
    limit = getattr(args, "search_game_budget", None)
    budgets = ({arm: SimulationBudget(limit) for arm in ("genetic", "gepa_genetic")}
               if limit is not None else {})
    evaluator = MatchupEvaluator(board, opponents, output / "traces",
                                 simulation_budget=budgets.get("gepa_genetic"),
                                 workers=args.workers if budgets else 1)
    resources.callback(evaluator.close)
    evaluator.info.strategy_schema_version = getattr(args, "genome_schema", 2)
    if json.loads(editable)["schema_version"] != evaluator.info.strategy_schema_version:
        raise ValueError("Seed genome schema must match --genome-schema")
    initial = compile_genome(editable, evaluator.info, "Shared typed engine seed")
    initial_seeds = distinct_seeds([initial, *[s for _, s in build_engine_seeds(board)]])
    if budgets:
        # Fail before making model requests if even the worst allowed GEPA
        # cost, first genetic cycle, and final selection cannot fit.
        n = len(opponents)
        top_k = max(1, int(round(args.population * 0.2)))
        minimum_cycle = (args.population + top_k) * args.train_games * n + args.validation_games * n
        required = (args.max_metric_calls * max(args.train_games, args.validation_games)
                    + minimum_cycle + (len(initial_seeds) + 2) * args.validation_games * n)
        if limit < required:
            raise ValueError(f"Search game budget must be at least {required} for these settings")
    (output / "initial-genome.json").write_text(editable)
    train = matchup_cases(opponents, seed, args.train_games, "train")
    validation = matchup_cases(opponents, seed, args.validation_games, "validation")
    test = matchup_cases(opponents, seed, args.test_games, "test")
    backend = getattr(args, "reflection_backend", "api")
    if backend == "codex":
        from dominion.simulation.codex_reflection import CodexReflection
        lm = CodexReflection(output / "codex-reflections", model=args.reflection_model,
                             timeout=args.reflection_timeout)
    else:
        from gepa.lm import LM
        lm = LM(args.reflection_model, max_tokens=4096, num_retries=0, timeout=120)
    started = time.monotonic()
    selected_text, gepa_metadata = optimize_strategy(
        evaluator, editable, train, validation, reflection_lm=lm,
        max_metric_calls=args.max_metric_calls,
        max_reflection_cost=args.max_reflection_cost if backend == "api" else None,
        run_dir=output / "gepa", seed=seed,
    )
    gepa_cost = {
        "elapsed_seconds": time.monotonic() - started,
        "simulated_games": evaluator.simulated_games,
        "billing_mode": "chatgpt_subscription" if backend == "codex" else "api",
        "estimated_api_cost_usd": lm.total_cost if backend == "api" else None,
        "input_tokens": lm.total_tokens_in if getattr(lm, "usage_reported", True) else None,
        "output_tokens": lm.total_tokens_out if getattr(lm, "usage_reported", True) else None,
        "reflection_calls": getattr(lm, "calls", None),
        "cached_input_tokens": getattr(lm, "cached_tokens_in", None),
        "cli_version": getattr(lm, "version", None),
    }
    # Persist before further simulation so API work is reviewable if GA fails.
    (output / "selected-genome.json").write_text(selected_text)
    (output / "gepa-result.json").write_text(json.dumps(gepa_metadata, indent=2))
    proposed = compile_genome(selected_text, evaluator.info, "GEPA proposed seed")
    novel = genome_signature(proposed) not in {genome_signature(s) for s in initial_seeds}
    # An unchanged proposal must not alter the initial population merely by
    # injecting a duplicate or changing the mutation stream during seeding.
    hybrid_seeds = distinct_seeds([proposed, *initial_seeds]) if novel else initial_seeds
    print(f"Seed {seed}: reflection completed ({gepa_cost['simulated_games']} games); starting genetic arms", flush=True)
    control, control_cost = genetic_search(
        board, opponents, initial_seeds, seed, args, output / "control",
        simulation_budget=budgets.get("genetic"),
        reserve_selection_games=(len(initial_seeds) + 1) * len(opponents) * args.validation_games if budgets else 0,
    )
    print(f"Seed {seed}: control training completed ({control_cost['evaluated_games']} games, "
          f"{control_cost['final_generation']} generations)", flush=True)
    hybrid, hybrid_cost = genetic_search(
        board, opponents, hybrid_seeds, seed, args, output / "hybrid",
        simulation_budget=budgets.get("gepa_genetic"),
        reserve_selection_games=(len(hybrid_seeds) + 1) * len(opponents) * args.validation_games if budgets else 0,
    )
    print(f"Seed {seed}: assisted training completed ({hybrid_cost['evaluated_games']} games, "
          f"{hybrid_cost['final_generation']} generations)", flush=True)
    # Select each genetic arm's recommendation on a shared validation panel,
    # keeping its starting strategies eligible if evolution regresses.
    recommendations = {}
    for arm, options in (
        ("genetic", [*initial_seeds, control]),
        ("gepa_genetic", [*hybrid_seeds, hybrid]),
    ):
        if budgets:
            options = distinct_seeds(options)
            evaluator.simulation_budget = budgets[arm]
            evaluator.budget_phase = "selection"
            selection_cases = budgeted_selection_cases(
                opponents, seed, args.validation_games, len(options), budgets[arm].remaining,
            )
        else:
            selection_cases = validation
        panels = [evaluator.panel(strategy, selection_cases) for strategy in options]
        best = max(range(len(panels)), key=lambda i: panels[i]["score"])
        recommendations[arm] = options[best]
        (output / f"{arm}-selection.json").write_text(json.dumps({
            "selected_index": best, "names": [s.name for s in options], "validation": panels,
            "games_per_opponent": selection_cases[0].games,
        }, indent=2))
    # Lock both recommendations before any held-out results are observed.
    import cloudpickle
    for arm, strategy in recommendations.items():
        (output / f"{arm}-strategy.pkl").write_bytes(cloudpickle.dumps(strategy))
    validation_games = evaluator.simulated_games - gepa_cost["simulated_games"]
    evaluator.simulation_budget = None  # Fresh evidence has its own fixed budget.
    print(f"Seed {seed}: recommendations locked; starting {args.test_games}-game fresh matchups", flush=True)
    tested = {arm: evaluator.panel(strategy, test) for arm, strategy in recommendations.items()}
    # Direct matchups cannot change selection. Matched-budget studies use a
    # separate random block; earlier pilot mode retains its recorded seeds.
    head_to_head = MatchupEvaluator(board, {"Genetic control": recommendations["genetic"]},
                                   output / "head-to-head", workers=args.workers if budgets else 1)
    resources.callback(head_to_head.close)
    direct_case = matchup_cases(head_to_head.opponents, game_seed(seed, 3) if budgets else seed,
                               args.test_games, "test")
    direct = head_to_head.panel(recommendations["gepa_genetic"], direct_case)
    report = {
        "seed": seed, "gepa_cost": gepa_cost, "control_cost": control_cost,
        "hybrid_cost": hybrid_cost, "selection_games": validation_games,
        "gepa_metric_calls": gepa_metadata["result"]["total_metric_calls"],
        "gepa_candidates": len(gepa_metadata["result"]["candidates"]),
        "novel_gepa_seed": novel,
        "selected_names": {arm: s.name for arm, s in recommendations.items()},
        "search_budgets": {arm: budget.snapshot() for arm, budget in budgets.items()},
        "held_out": tested, "hybrid_vs_control": direct,
        "total_simulated_games": evaluator.simulated_games + head_to_head.simulated_games
        + control_cost["evaluated_games"] + hybrid_cost["evaluated_games"],
    }
    (output / "evaluation-records.json").write_text(json.dumps(evaluator.records, indent=2))
    (output / "summary.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description="GEPA-proposed strategy seeds versus genetic search")
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--reflection-backend", choices=["codex", "api"], default="codex",
                        help="Codex uses saved ChatGPT sign-in; api uses LiteLLM")
    parser.add_argument("--reflection-model",
                        help="Optional Codex model override; required provider/model for api")
    parser.add_argument("--reflection-timeout", type=int, default=300,
                        help="Seconds per Codex reflection request")
    parser.add_argument("--seed-genome", type=Path)
    parser.add_argument("--genome-schema", type=int, choices=[1, 2], default=2,
                        help="Schema 1 preserves the earlier pilot's search decisions")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--max-metric-calls", type=int, default=12, help="Per seed; one call is one opponent matchup")
    parser.add_argument("--max-reflection-cost", type=float, default=0.5,
                        help="Per-seed estimated USD stop threshold; one request can cross it")
    parser.add_argument("--train-games", type=int, default=10, help="Per opponent")
    parser.add_argument("--validation-games", type=int, default=100, help="Per opponent")
    parser.add_argument("--test-games", type=int, default=400, help="Per opponent and direct matchup")
    parser.add_argument("--population", type=int, default=12)
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--workers", type=int, default=1, help="Genetic evaluator processes")
    parser.add_argument("--search-game-budget", type=int,
                        help="Hard games per arm/seed, including GEPA, genetic search and selection; fixed opponent panel")
    parser.add_argument("--output", type=Path, required=True, help="New experiment directory")
    args = parser.parse_args()
    if args.reflection_backend == "api" and not args.reflection_model:
        parser.error("--reflection-model is required for the api backend")
    if args.reflection_timeout <= 0:
        parser.error("--reflection-timeout must be positive")
    for attr in ("train_games", "validation_games", "test_games"):
        value = getattr(args, attr)
        if value < 2 or value % 2:
            parser.error(f"--{attr.replace('_', '-')} must be a positive even number")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds must be distinct")
    if args.population < 5 or args.generations < 1:
        parser.error("Use population >= 5 and generations >= 1")
    if args.search_game_budget is not None and args.search_game_budget <= 0:
        parser.error("--search-game-budget must be positive")
    if args.reflection_backend == "api" and args.max_reflection_cost <= 0:
        parser.error("API reflection cost threshold must be positive")
    if args.output.exists():
        parser.error("--output must be a new directory; existing experiments are never overwritten")
    board = load_board(args.board)
    loader = StrategyLoader()
    opponents = {}
    for name in ["Big Money", *args.reference]:
        strategy = loader.get_strategy(name)
        if strategy is None:
            parser.error(f"Unknown reference strategy: {name}")
        opponents[name] = strategy
    for name, strategy in build_engine_seeds(board, max_engines=2):
        opponents.setdefault(name, strategy)
    if args.max_metric_calls < 2 * len(opponents) + 2:
        parser.error("Metric budget must cover initial panel and one fully validated proposal")
    # Validate optional dependencies before creating an experiment directory.
    try:
        importlib.metadata.version("gepa")
        if args.reflection_backend == "api":
            importlib.metadata.version("litellm")
    except importlib.metadata.PackageNotFoundError:
        extra = "gepa-api" if args.reflection_backend == "api" else "gepa"
        parser.error(f"Install dependencies: python -m pip install -e '.[{extra}]'")
    args.output.mkdir(parents=True)
    manifest = {
        "command": shlex.join([sys.executable, *sys.argv]), "board": asdict(board),
        "settings": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "opponents": list(opponents),
        "versions": {name: importlib.metadata.version(name) for name in
                     (("gepa", "litellm") if args.reflection_backend == "api" else ("gepa",))},
        "simulation_fingerprint": tournament_fingerprint(),
        "comparison": ("Equal hard search-game allowances; GEPA games count against the assisted arm; fixed panel; "
                       "remaining games fund balanced selection; unused residual is reported"
                       if args.search_game_budget is not None else
                       "GEPA adds compute and one initial seed; genetic settings are shared"),
        "scoring": "Existing simulator wins, including its seat-order fallback for full ties; seat balanced",
        "analysis_plan": {
            "primary": "Mean assisted-vs-control fresh win rate across search seeds",
            "uncertainty": "95% Student-t interval across seed-level rates; shuffle pairs are dependent",
            "secondary": "Paired panel mean and robust score differences, and each strong reference matchup",
            "direct_random_block": "separate" if args.search_game_budget is not None else "first panel opponent block",
            "selection": "Recommendations locked before fresh games; no holdout tuning",
        },
        "results": [],
    }
    manifest_path = args.output / "experiment.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    for seed in args.seeds:
        try:
            report = run_seed(board, opponents, seed, args, args.output / f"seed-{seed}")
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["failed_seed"] = seed
            manifest["error_type"] = type(exc).__name__
            manifest_path.write_text(json.dumps(manifest, indent=2))
            raise
        manifest["results"].append(report)
        manifest_path.write_text(json.dumps(manifest, indent=2))
    manifest["status"] = "complete"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Experiment written to {manifest_path}")


if __name__ == "__main__":
    main()
