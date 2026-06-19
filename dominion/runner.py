import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import coloredlogs
import yaml

from dominion.boards.loader import BoardConfig, load_board
from dominion.analysis.strategy_library import find_compatible_strategies
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule, WayRule
from dominion.strategy.lint import cleanup_for_publication, lint_strategy

logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger)


def load_kingdom_cards_from_yaml(yaml_path: str) -> tuple[list[str], dict]:
    """Load kingdom cards and optional training parameters from a YAML file."""
    try:
        with open(yaml_path, 'r', encoding="utf-8") as file:
            data = yaml.safe_load(file)
            if 'kingdom_cards' not in data:
                raise ValueError("YAML file must contain 'kingdom_cards' key")

            kingdom_cards = data['kingdom_cards']
            training_params = data.get('training_parameters', {})

            return kingdom_cards, training_params
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")


def save_strategy_as_python(
    strategy: EnhancedStrategy,
    path: Path,
    class_name: str = "GeneratedStrategy",
    *,
    clean_for_publication: bool = True,
    board_config: BoardConfig | None = None,
) -> None:
    """Serialize an EnhancedStrategy as a Python module."""
    if clean_for_publication:
        strategy = cleanup_for_publication(strategy, board_config=board_config)

    def format_list(name: str, rules: list[PriorityRule]) -> list[str]:
        lines = [f"        self.{name} = ["]
        for rule in rules:
            cond_source = getattr(rule.condition, "_source", None) if rule.condition else None
            if cond_source:
                lines.append(f"            PriorityRule({rule.card_name!r}, {cond_source}),")
            else:
                lines.append(f"            PriorityRule({rule.card_name!r}),")
        lines.append("        ]")
        return lines

    def format_way_policy(rules: list[WayRule]) -> list[str]:
        lines = ["        self.way_policy = ["]
        for rule in rules:
            cond_source = getattr(rule.condition, "_source", None) if rule.condition else None
            if cond_source:
                lines.append(
                    f"            WayRule({rule.card_name!r}, {rule.way_name!r}, {cond_source}),"
                )
            else:
                lines.append(
                    f"            WayRule({rule.card_name!r}, {rule.way_name!r}),"
                )
        lines.append("        ]")
        return lines

    needs_way_rule = bool(getattr(strategy, "way_policy", None))
    import_line = (
        "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule, WayRule"
        if needs_way_rule
        else "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule"
    )
    lines = [
        import_line,
        "",
        "",
        f"class {class_name}(EnhancedStrategy):",
        "    def __init__(self) -> None:",
        "        super().__init__()",
        f"        self.name = {strategy.name!r}",
        "        self.description = \"Auto-generated strategy from genetic training\"",
        "        self.version = \"1.0\"",
        "",
    ]

    if strategy.gain_priority:
        lines.extend(format_list("gain_priority", strategy.gain_priority))
        lines.append("")
    if strategy.action_priority:
        lines.extend(format_list("action_priority", strategy.action_priority))
        lines.append("")
    if strategy.treasure_priority:
        lines.extend(format_list("treasure_priority", strategy.treasure_priority))
        lines.append("")
    if strategy.trash_priority:
        lines.extend(format_list("trash_priority", strategy.trash_priority))
        lines.append("")
    if getattr(strategy, "discard_priority", None):
        lines.extend(format_list("discard_priority", strategy.discard_priority))
        lines.append("")
    if needs_way_rule:
        lines.extend(format_way_policy(strategy.way_policy))
        lines.append("")

    lines.extend(
        [
            f"def create_{class_name.lower()}() -> EnhancedStrategy:",
            f"    return {class_name}()",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def merge_baseline_panel(base_panel: list, reused: list) -> list:
    """Return ``base_panel`` followed by the ``reused`` strategies not already
    present (dedup by ``strategy.name``).

    Pulled out of ``main()`` so the reuse-augments-default-baselines invariant
    is unit-testable without standing up an argparse/training run: with reuse on
    and no explicit baseline, the resolved panel must contain the default
    baselines (Big Money etc.) ALONGSIDE the reused strategies, never the reused
    strategies alone.
    """
    panel = list(base_panel)
    existing_names = {strategy.name for strategy in panel}
    for strategy in reused:
        if strategy.name in existing_names:
            continue
        existing_names.add(strategy.name)
        panel.append(strategy)
    return panel


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Train a Dominion strategy using genetic algorithms")
    parser.add_argument("--kingdom-cards", nargs="+", help="List of kingdom cards to use for training")
    parser.add_argument("--config", "-c", help="YAML configuration file containing kingdom cards")
    parser.add_argument(
        "--population-size", type=int, default=25, help="Population size for genetic algorithm (default: 25)"
    )
    parser.add_argument("--generations", type=int, default=40, help="Number of generations to run (default: 40)")
    parser.add_argument("--mutation-rate", type=float, default=0.1, help="Mutation rate (default: 0.1)")
    parser.add_argument(
        "--games-per-eval",
        type=int,
        default=None,
        help="Number of games to play per strategy evaluation (default: config value, else 30)",
    )
    parser.add_argument("--board", help="Board definition file containing kingdom cards and landscapes")
    parser.add_argument(
        "--seed-strategy",
        help="Python module path to a strategy factory function to inject into the initial population "
        "(e.g. generated_strategies.torture_campaign_v2:create_torture_campaign_v2)",
    )
    parser.add_argument(
        "--seed-strategies",
        nargs="+",
        help="Additional module:function seed strategies to inject into the initial population.",
    )
    parser.add_argument(
        "--reuse-compatible-strategies",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically reuse existing strategies whose referenced cards overlap this board. "
        "Selected strategies are injected as seeds and added to the baseline panel. "
        "On by default; disable with --no-reuse-compatible-strategies.",
    )
    parser.add_argument(
        "--trick-seeds",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Seed the population with trick-scanner-derived strategies when --board is given "
        "(one seed per surfaced mechanical interaction). On by default; disable with "
        "--no-trick-seeds.",
    )
    parser.add_argument(
        "--reuse-top-k",
        type=int,
        default=3,
        help="Maximum compatible strategies to reuse when --reuse-compatible-strategies is set (default: 3).",
    )
    parser.add_argument(
        "--reuse-min-overlap",
        type=int,
        default=2,
        help="Minimum non-base card overlap for automatic strategy reuse (default: 2).",
    )
    parser.add_argument(
        "--baseline-strategy",
        help="Python module path to a strategy factory function to evaluate against instead of Big Money "
        "(e.g. generated_strategies.torture_campaign_v2:create_torture_campaign_v2)",
    )
    parser.add_argument(
        "--baseline-panel",
        nargs="+",
        help="Multiple module:function specs evaluated as a panel of opponents. Games are split "
        "evenly across the panel; fitness is the mean per-opponent win rate. Overrides --baseline-strategy.",
    )

    args = parser.parse_args()

    # Determine kingdom cards from arguments, config file, or defaults
    kingdom_cards = None
    board_config: BoardConfig | None = None
    training_params = {}

    if args.board:
        try:
            board_config = load_board(args.board)
            kingdom_cards = board_config.kingdom_cards
            logger.info("Using board %s: %s", args.board, ", ".join(kingdom_cards))
            if board_config.ways:
                logger.info("  Ways: %s", ", ".join(board_config.ways))
            if board_config.projects:
                logger.info("  Projects: %s", ", ".join(board_config.projects))
            if board_config.events:
                logger.info("  Events: %s", ", ".join(board_config.events))
        except (FileNotFoundError, ValueError) as exc:
            logger.error("Error loading board: %s", exc)
            sys.exit(1)

    if args.kingdom_cards:
        kingdom_cards = args.kingdom_cards
        logger.info("Using kingdom cards from command line: %s", ", ".join(kingdom_cards))
        board_config = None
    elif args.config and not board_config:
        try:
            kingdom_cards, training_params = load_kingdom_cards_from_yaml(args.config)
            logger.info("Using kingdom cards from %s: %s", args.config, ", ".join(kingdom_cards))
            if training_params:
                logger.info("Loaded training parameters from config file")
        except (FileNotFoundError, ValueError) as e:
            logger.error("Error loading config file: %s", e)
            sys.exit(1)
    if kingdom_cards is None:
        # Default kingdom cards
        kingdom_cards = [
            "Village",
            "Smithy",
            "Market",
            "Festival",
            "Laboratory",
            "Mine",
            "Witch",
            "Moat",
            "Workshop",
            "Chapel",
        ]
        logger.info("Using default kingdom cards: %s", ", ".join(kingdom_cards))

    if board_config is None:
        board_config = BoardConfig(list(kingdom_cards))

    # Use parameters from command line args, falling back to YAML config, then defaults
    population_size = args.population_size or training_params.get('population_size', 5)
    generations = args.generations or training_params.get('generations', 10)
    mutation_rate = args.mutation_rate or training_params.get('mutation_rate', 0.1)
    # 10-game screens were pure noise (win-rate sd ~15pp); 30 is the floor at
    # which racing's refine/confirm stages can rescue the comparisons.
    games_per_eval = args.games_per_eval or training_params.get('games_per_eval', 30)

    # Create trainer with parameters
    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=population_size,
        generations=generations,
        mutation_rate=mutation_rate,
        games_per_eval=games_per_eval,
        board_config=board_config,
        default_baseline_panel=True,
    )

    # Load strategies from module:function paths
    def _load_strategy(spec: str):
        module_path, func_name = spec.rsplit(":", 1)
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, func_name)()

    reusable_entries = []
    if args.reuse_compatible_strategies:
        try:
            reusable_entries = find_compatible_strategies(
                kingdom_cards,
                top_k=args.reuse_top_k,
                min_overlap=args.reuse_min_overlap,
            )
            if reusable_entries:
                logger.info(
                    "Reusable strategy seeds: %s",
                    ", ".join(
                        f"{entry.name} ({', '.join(sorted(entry.matched_cards))})"
                        for entry in reusable_entries
                    ),
                )
            else:
                logger.info("No reusable strategies met the compatibility threshold")
        except Exception as exc:
            # Reuse is a default-on enrichment, not a precondition — a broken
            # strategy file in the library must not kill the training run.
            logger.warning("Skipping strategy reuse — discovery failed: %s", exc)
            reusable_entries = []

    # Inject seed strategies if provided or discovered
    seed_specs = []
    if args.seed_strategy:
        seed_specs.append(args.seed_strategy)
    if args.seed_strategies:
        seed_specs.extend(args.seed_strategies)
    seed_specs.extend(entry.spec for entry in reusable_entries)

    seen_seed_specs: set[str] = set()
    for spec in seed_specs:
        if spec in seen_seed_specs:
            continue
        seen_seed_specs.add(spec)
        try:
            seed = _load_strategy(spec)
            trainer.inject_strategy(seed)
            logger.info("Injected seed strategy: %s", seed.name)
        except Exception as exc:
            logger.error("Failed to load seed strategy %s: %s", spec, exc)
            sys.exit(1)

    # Trick-scanner seeds: one strategy per mechanical interaction surfaced
    # on this board, so the GA starts with the trick encoded instead of
    # having to rediscover it by random mutation. Mirrors evolve.py.
    if args.trick_seeds and args.board and board_config is not None:
        from dominion.analysis.seed_genomes import build_seed_genomes

        try:
            trick_seeds = build_seed_genomes(board_config)
        except Exception as exc:
            logger.warning("Skipping trick seeds — scanner failed: %s", exc)
            trick_seeds = []
        if trick_seeds:
            trainer.inject_strategies([strategy for _, strategy in trick_seeds])
            logger.info(
                "Injected trick-scanner seeds: %s",
                ", ".join(name for name, _ in trick_seeds),
            )
        else:
            logger.info("Trick scanner surfaced no interactions for this board")

    # Establish the baseline panel BEFORE folding in reused strategies, so
    # reuse ADDS TO the panel instead of replacing it. Precedence for the base
    # panel: explicit --baseline-panel > explicit --baseline-strategy > the
    # trainer's default baseline panel (Big Money + compatible built-ins).
    panel: list = []
    if args.baseline_panel:
        try:
            panel = [_load_strategy(spec) for spec in args.baseline_panel]
            logger.info("Evaluating against panel: %s", ", ".join(p.name for p in panel))
        except Exception as exc:
            logger.error("Failed to load baseline panel: %s", exc)
            sys.exit(1)
    elif args.baseline_strategy:
        try:
            panel = [_load_strategy(args.baseline_strategy)]
            logger.info("Evaluating against baseline: %s", panel[0].name)
        except Exception as exc:
            logger.error("Failed to load baseline strategy: %s", exc)
            sys.exit(1)
    elif trainer.default_baseline_panel:
        panel = trainer.build_default_baseline_panel()
        if panel:
            logger.info("Using default baseline panel: %s", ", ".join(p.name for p in panel))

    if reusable_entries:
        reused_panel_specs = [
            entry.spec
            for entry in reusable_entries
            if entry.spec not in set(args.baseline_panel or [])
        ]
        try:
            reused_panel = [_load_strategy(spec) for spec in reused_panel_specs]
        except Exception as exc:
            logger.error("Failed to load reusable baseline strategy: %s", exc)
            sys.exit(1)
        # Dedup by name so a strategy that is both a default baseline and a
        # reuse entry is not doubled into the panel.
        before_names = {strategy.name for strategy in panel}
        panel = merge_baseline_panel(panel, reused_panel)
        added = [strategy for strategy in panel if strategy.name not in before_names]
        if added:
            logger.info(
                "Added reusable strategies to baseline panel: %s",
                ", ".join(strategy.name for strategy in added),
            )

    # Commit the assembled panel to the trainer. Mirror the historical
    # len(panel) > 1 split: a lone member becomes the single baseline.
    if len(panel) > 1:
        trainer.set_baseline_panel(panel)
    elif panel:
        trainer.set_baseline_strategy(panel[0])

    logger.info("Training parameters:")
    logger.info("  Population size: %d", population_size)
    logger.info("  Generations: %d", generations)
    logger.info("  Mutation rate: %s", mutation_rate)
    logger.info("  Games per evaluation: %d", games_per_eval)

    # Run training
    best_strategy, metrics = trainer.train()

    logger.info("Training complete!")
    logger.info("Final metrics: %s", metrics)

    if best_strategy is None:
        logger.info("No viable strategy was found.")
    else:
        best_strategy = cleanup_for_publication(best_strategy, board_config=board_config)
        lint_warnings = lint_strategy(best_strategy)
        if lint_warnings:
            logger.info("Strategy lint diagnostics:")
            for warning in lint_warnings[:10]:
                logger.info(
                    "  [%s] %s[%d] %s: %s",
                    warning.severity,
                    warning.list_name,
                    warning.index,
                    warning.card_name,
                    warning.message,
                )
            if len(lint_warnings) > 10:
                logger.info("  ... %d more diagnostics", len(lint_warnings) - 10)

        logger.info("Best strategy card priorities:")
        for rule in best_strategy.gain_priority:
            condition_str = f" (condition: {rule.condition})" if rule.condition else ""
            logger.info("  %s%s", rule.card_name, condition_str)

        # Validate against panel (or single baseline) and report — always save.
        if panel:
            from dominion.simulation.strategy_battle import StrategyBattle
            from dominion.ai.genetic_ai import GeneticAI
            from dominion.simulation.genetic_trainer import _distribute_games

            n_validation = 100
            games_for_opp = _distribute_games(n_validation, len(panel))
            logger.info(
                "Validating: %d games distributed across %d-strategy panel (%s)...",
                sum(games_for_opp), len(panel), games_for_opp,
            )
            validation_battle = StrategyBattle(board_config=board_config, log_frequency=1000)
            validation_kingdom = board_config.kingdom_cards if board_config else kingdom_cards
            # List of (name, rate) so panel members sharing a name (e.g. two
            # BigMoneySmithy variants) each contribute independently to the mean.
            per_opp: list[tuple[str, float]] = []
            for idx, opp in enumerate(panel):
                games_per_opp = games_for_opp[idx]
                wins = 0
                for i in range(games_per_opp):
                    ai1 = GeneticAI(best_strategy)
                    ai2 = GeneticAI(opp)
                    if i % 2 == 0:
                        winner, _, _, _ = validation_battle.run_game(ai1, ai2, validation_kingdom)
                    else:
                        winner, _, _, _ = validation_battle.run_game(ai2, ai1, validation_kingdom)
                    if winner == ai1:
                        wins += 1
                rate = wins / games_per_opp * 100
                per_opp.append((opp.name, rate))
                logger.info("  vs %s: %.1f%%", opp.name, rate)
            mean_rate = sum(r for _, r in per_opp) / len(per_opp)
            logger.info("Validation mean win rate: %.1f%%", mean_rate)
            if mean_rate <= 50:
                logger.info("⚠️  Strategy did not beat panel mean (%.1f%%). Saving anyway for inspection.", mean_rate)

        # Automatically save the strategy as a Python class
        strategies_dir = Path("generated_strategies")
        strategies_dir.mkdir(exist_ok=True)

        # Create a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_filename = f"strategy_{timestamp}.py"
        strategy_path = strategies_dir / strategy_filename
        class_name = f"Strategy{timestamp}"

        # Save the strategy
        try:
            save_strategy_as_python(
                best_strategy,
                strategy_path,
                class_name,
                board_config=board_config,
            )
            logger.info("✅ Strategy automatically saved to: %s", strategy_path)
            logger.info("Class name: %s", class_name)
            logger.info("Win rate vs BigMoney: %.1f%%", metrics.get('win_rate', 0.0))
        except Exception:
            logger.exception("❌ Error saving strategy")


if __name__ == "__main__":
    main()
