"""Tournament + genetic evolution pipeline.

1. Round-robin tournament between seed strategies
2. Genetic evolution seeded with each, using the best seed as baseline
3. Final tournament of all seeds + evolved strategies

Usage:
    python evolve.py --board boards/siege_engine.txt \
        --seeds generated_strategies.siege_engine_v1:create_siege_engine_v1 \
               generated_strategies.siege_engine_v2:create_siege_engine_v2 \
               generated_strategies.siege_engine_v3:create_siege_engine_v3 \
        --population 25 --generations 80 --games-per-eval 100 \
        --tournament-games 2000
"""

import argparse
import importlib
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import coloredlogs

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.reporting.html_report import generate_leaderboard_html
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from runner import save_strategy_as_python

logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger)


def _load_factory(spec: str):
    """Load a module:function spec and return the callable."""
    module_path, func_name = spec.rsplit(":", 1)
    mod = importlib.import_module(module_path)
    return getattr(mod, func_name)


def _short_name(spec: str) -> str:
    """Extract a readable name from a module:function spec."""
    func = spec.rsplit(":", 1)[1]
    # create_siege_engine_v1 -> siege_engine_v1
    name = func.removeprefix("create_").removeprefix("Create")
    return name.replace("_", " ").title()


def run_matchup(battle, factory_a, factory_b, num_games):
    """Run a head-to-head matchup, return (a_wins, b_wins)."""
    kingdom = battle.board_config.kingdom_cards if battle.board_config else None
    a_wins = 0
    for i in range(num_games):
        ai_a = GeneticAI(factory_a())
        ai_b = GeneticAI(factory_b())
        if i % 2 == 0:
            winner, _, _, _ = battle.run_game(ai_a, ai_b, kingdom)
        else:
            winner, _, _, _ = battle.run_game(ai_b, ai_a, kingdom)
        if winner == ai_a:
            a_wins += 1
    return a_wins, num_games - a_wins


def round_robin(strategies, battle, num_games):
    """Run a round-robin tournament, return {name: {wins, losses, win_rate}}."""
    names = list(strategies.keys())
    results = {n: {"wins": 0, "losses": 0} for n in names}

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            na, nb = names[i], names[j]
            logger.info("  %s vs %s (%d games)...", na, nb, num_games)
            a_wins, b_wins = run_matchup(
                battle, strategies[na], strategies[nb], num_games
            )
            results[na]["wins"] += a_wins
            results[na]["losses"] += b_wins
            results[nb]["wins"] += b_wins
            results[nb]["losses"] += a_wins
            logger.info(
                "    %s: %d wins (%.1f%%) | %s: %d wins (%.1f%%)",
                na, a_wins, a_wins / num_games * 100,
                nb, b_wins, b_wins / num_games * 100,
            )

    for name, stats in results.items():
        total = stats["wins"] + stats["losses"]
        stats["win_rate"] = stats["wins"] / total * 100 if total else 0

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Tournament + genetic evolution pipeline"
    )
    parser.add_argument(
        "--board", required=True,
        help="Board definition file (e.g. boards/siege_engine.txt)",
    )
    parser.add_argument(
        "--seeds", required=True, nargs="+",
        help="module:function specs for seed strategy factories",
    )
    parser.add_argument(
        "--population", type=int, default=25,
        help="Genetic algorithm population size (default: 25)",
    )
    parser.add_argument(
        "--generations", type=int, default=80,
        help="Number of generations to evolve (default: 80)",
    )
    parser.add_argument(
        "--games-per-eval", type=int, default=100,
        help="Games per fitness evaluation (default: 100)",
    )
    parser.add_argument(
        "--mutation-rate", type=float, default=0.15,
        help="Mutation rate (default: 0.15)",
    )
    parser.add_argument(
        "--tournament-games", type=int, default=2000,
        help="Games per matchup in tournaments (default: 2000)",
    )
    parser.add_argument(
        "--validation-games", type=int, default=200,
        help="Games to validate each evolved strategy (default: 200)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("generated_strategies"),
        help="Directory to save evolved strategies (default: generated_strategies/)",
    )

    args = parser.parse_args()

    board_config = load_board(args.board)
    board_name = Path(args.board).stem

    # Load seed strategies
    seeds = {}
    for spec in args.seeds:
        name = _short_name(spec)
        seeds[name] = _load_factory(spec)

    if len(seeds) < 2:
        logger.error("Need at least 2 seed strategies for a tournament")
        return

    battle = StrategyBattle(board_config=board_config, log_frequency=0)

    # --- Phase 1: Seed Tournament ---
    logger.info("=" * 60)
    logger.info("PHASE 1: Seed Tournament (%d games per matchup)", args.tournament_games)
    logger.info("  Board: %s", args.board)
    logger.info("  Seeds: %s", ", ".join(seeds.keys()))
    logger.info("=" * 60)

    seed_results = round_robin(seeds, battle, args.tournament_games)

    logger.info("\nSeed Rankings:")
    ranked = sorted(seed_results.items(), key=lambda x: x[1]["win_rate"], reverse=True)
    for rank, (name, stats) in enumerate(ranked, 1):
        logger.info(
            "  #%d %s: %d-%d (%.1f%%)",
            rank, name, stats["wins"], stats["losses"], stats["win_rate"],
        )

    best_seed_name = ranked[0][0]
    best_seed_factory = seeds[best_seed_name]
    logger.info("\nBest seed: %s", best_seed_name)

    # --- Phase 2: Genetic Evolution ---
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2: Genetic Evolution (seeded with each strategy)")
    logger.info("  Population: %d | Generations: %d | Games/eval: %d | Mutation: %.2f",
                args.population, args.generations, args.games_per_eval, args.mutation_rate)
    logger.info("  Baseline: %s", best_seed_name)
    logger.info("=" * 60)

    evolved = {}
    args.output_dir.mkdir(exist_ok=True)

    baseline = best_seed_factory()

    for seed_name, seed_factory in seeds.items():
        logger.info("\nEvolving from: %s", seed_name)

        trainer = GeneticTrainer(
            kingdom_cards=board_config.kingdom_cards,
            population_size=args.population,
            generations=args.generations,
            mutation_rate=args.mutation_rate,
            games_per_eval=args.games_per_eval,
            board_config=board_config,
        )
        trainer.inject_strategy(seed_factory())
        trainer.set_baseline_strategy(baseline)

        best_strategy, metrics = trainer.train()

        if best_strategy is None:
            logger.info("  No viable strategy evolved from %s", seed_name)
            continue

        # Validate evolved strategy against baseline
        kingdom = board_config.kingdom_cards
        wins = 0
        for i in range(args.validation_games):
            ai1 = GeneticAI(best_strategy)
            ai2 = GeneticAI(best_seed_factory())
            if i % 2 == 0:
                winner, _, _, _ = battle.run_game(ai1, ai2, kingdom)
            else:
                winner, _, _, _ = battle.run_game(ai2, ai1, kingdom)
            if winner == ai1:
                wins += 1
        win_rate = wins / args.validation_games * 100
        logger.info("  Evolved from %s: %.1f%% vs best seed", seed_name, win_rate)

        evolved_name = f"Evolved {seed_name}"
        evolved[evolved_name] = best_strategy

        # Save the strategy
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = seed_name.lower().replace(" ", "_")
        filename = f"{board_name}_evolved_{slug}_{timestamp}.py"
        class_name = f"Evolved{slug.title().replace('_', '')}"
        save_strategy_as_python(best_strategy, args.output_dir / filename, class_name)
        logger.info("  Saved: %s", filename)

    # --- Phase 3: Final Tournament ---
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3: Final Tournament (seeds + evolved, %d games each)", args.tournament_games)
    logger.info("=" * 60)

    all_strategies = {}
    for name, factory in seeds.items():
        all_strategies[name] = factory
    for name, strat in evolved.items():
        s = strat
        all_strategies[name] = lambda _s=s: deepcopy(_s)

    final_results = round_robin(all_strategies, battle, args.tournament_games)

    logger.info("\nFinal Rankings:")
    final_ranked = sorted(final_results.items(), key=lambda x: x[1]["win_rate"], reverse=True)
    for rank, (name, stats) in enumerate(final_ranked, 1):
        logger.info(
            "  #%d %s: %d-%d (%.1f%%)",
            rank, name, stats["wins"], stats["losses"], stats["win_rate"],
        )

    # Generate leaderboard report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path("reports") / f"{board_name}_tournament_{timestamp}.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_leaderboard_html(final_results, report_path, verbose=True)


if __name__ == "__main__":
    main()
