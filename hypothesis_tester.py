"""Reusable hypothesis tester for strategy tuning.

Sweeps a parameter on a single rule, battles each variant against a baseline,
and produces an HTML comparison report.
"""

import argparse
import importlib
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.reporting.html_report import generate_sweep_report
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

logger = logging.getLogger(__name__)


class HypothesisTester:
    """Sweep a single parameter and battle variants against a baseline."""

    def __init__(
        self,
        board: Optional[str] = None,
        games: int = 500,
    ) -> None:
        self.board = board
        self.games = games

    def sweep(
        self,
        base_factory: Callable[[], EnhancedStrategy],
        list_name: str,
        card_name: str,
        condition_factory: Callable[[Any], Callable],
        values: list,
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Sweep a condition parameter and battle each variant against the baseline.

        Parameters:
            base_factory: Callable that returns a fresh EnhancedStrategy.
            list_name: Priority list to modify (e.g. "gain_priority").
            card_name: Card name whose rule receives the new condition.
            condition_factory: Callable(value) -> condition callable.
            values: List of parameter values to sweep.
            labels: Optional display labels for each value.

        Returns:
            Dict with sweep results suitable for ``generate_sweep_report``.
        """
        if labels is None:
            labels = [str(v) for v in values]
        if len(labels) != len(values):
            raise ValueError("labels and values must have the same length")

        # Build variant factories: first value is baseline (no modification)
        variants: dict[str, Callable[[], EnhancedStrategy]] = {}
        for value, label in zip(values, labels):
            if value == 0 or value is None:
                variants[label] = base_factory
            else:

                def _make_factory(val=value):
                    def factory():
                        strat = deepcopy(base_factory())
                        rules = getattr(strat, list_name)
                        for rule in rules:
                            if rule.card_name == card_name:
                                new_cond = condition_factory(val)
                                if rule.condition is not None:
                                    rule.condition = PriorityRule.and_(
                                        rule.condition, new_cond
                                    )
                                else:
                                    rule.condition = new_cond
                                break
                        return strat

                    return factory

                variants[label] = _make_factory()

        return self.compare(variants=variants)

    def compare(
        self,
        variants: dict[str, Callable[[], EnhancedStrategy]],
        board: Optional[str] = None,
        games: Optional[int] = None,
    ) -> dict[str, Any]:
        """Battle named variants against the first (baseline).

        Parameters:
            variants: Ordered dict mapping name -> strategy factory.
            board: Board file override (falls back to instance default).
            games: Number of games override (falls back to instance default).

        Returns:
            Dict with comparison results suitable for ``generate_sweep_report``.
        """
        board_path = board or self.board
        num_games = games or self.games

        board_config = load_board(board_path) if board_path else None

        battle = StrategyBattle(
            board_config=board_config,
            log_frequency=0,
        )

        names = list(variants.keys())
        baseline_name = names[0]
        baseline_factory = variants[baseline_name]

        all_results: list[dict[str, Any]] = []

        for name in names:
            factory = variants[name]
            is_baseline = name == baseline_name
            entry: dict[str, Any] = {
                "name": name,
                "is_baseline": is_baseline,
                "wins": 0,
                "losses": 0,
                "total_score": 0,
                "baseline_total_score": 0,
                "detailed_results": [],
            }

            if is_baseline:
                # Baseline vs itself: report 50% by convention
                entry["wins"] = num_games // 2
                entry["losses"] = num_games - num_games // 2
                entry["win_rate"] = 50.0
                entry["avg_score"] = 0.0
                entry["avg_baseline_score"] = 0.0
                entry["p_value"] = 1.0
                all_results.append(entry)
                continue

            kingdom_cards = board_config.kingdom_cards if board_config else None

            for game_num in range(num_games):
                variant_strat = factory()
                baseline_strat = baseline_factory()
                ai_variant = GeneticAI(variant_strat)
                ai_baseline = GeneticAI(baseline_strat)

                if game_num % 2 == 0:
                    winner, scores, _, turns = battle.run_game(
                        ai_variant, ai_baseline, kingdom_cards
                    )
                else:
                    winner, scores, _, turns = battle.run_game(
                        ai_baseline, ai_variant, kingdom_cards
                    )

                variant_won = winner == ai_variant
                variant_score = scores[ai_variant.name]
                baseline_score = scores[ai_baseline.name]

                entry["total_score"] += variant_score
                entry["baseline_total_score"] += baseline_score

                if variant_won:
                    entry["wins"] += 1
                else:
                    entry["losses"] += 1

                entry["detailed_results"].append(
                    {
                        "game_number": game_num + 1,
                        "variant_won": variant_won,
                        "variant_score": variant_score,
                        "baseline_score": baseline_score,
                        "margin": variant_score - baseline_score,
                        "turns": turns,
                    }
                )

            entry["win_rate"] = entry["wins"] / num_games * 100
            entry["avg_score"] = entry["total_score"] / num_games
            entry["avg_baseline_score"] = entry["baseline_total_score"] / num_games

            # p-value via binomial test
            from scipy.stats import binomtest

            entry["p_value"] = binomtest(
                entry["wins"], num_games, p=0.5, alternative="two-sided"
            ).pvalue

            logger.info(
                "%s: %d/%d (%.1f%%) p=%.4f",
                name,
                entry["wins"],
                num_games,
                entry["win_rate"],
                entry["p_value"],
            )

            all_results.append(entry)

        return {
            "baseline_name": baseline_name,
            "games_per_matchup": num_games,
            "variants": all_results,
        }


def _load_strategy(spec: str) -> Callable[[], EnhancedStrategy]:
    """Load a module:function spec and return the factory callable."""
    module_path, func_name = spec.rsplit(":", 1)
    mod = importlib.import_module(module_path)
    return getattr(mod, func_name)


def main():
    parser = argparse.ArgumentParser(
        description="Sweep a parameter on a strategy rule and compare variants"
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="module:function spec for the base strategy factory "
        "(e.g. generated_strategies.torture_campaign_v4:create_torture_campaign_v4)",
    )
    parser.add_argument(
        "--board",
        help="Board definition file (e.g. boards/torture_campaign.txt)",
    )
    parser.add_argument(
        "--list",
        dest="list_name",
        required=True,
        help="Priority list to modify (e.g. gain_priority)",
    )
    parser.add_argument(
        "--card",
        required=True,
        help="Card name whose rule receives the condition (e.g. Gold)",
    )
    parser.add_argument(
        "--condition",
        required=True,
        help="PriorityRule method call with {x} placeholder "
        "(e.g. \"has_cards(['Patrol'], {x})\")",
    )
    parser.add_argument(
        "--values",
        required=True,
        help="Comma-separated parameter values to sweep (e.g. 0,1,2,3,4)",
    )
    parser.add_argument(
        "--labels",
        help="Comma-separated labels for each value (optional)",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=500,
        help="Number of games per matchup (default: 500)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML file path (default: auto-generated in reports/)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    factory = _load_strategy(args.strategy)

    # Parse values (try int, fall back to string)
    raw_values = args.values.split(",")
    values = []
    for v in raw_values:
        v = v.strip()
        try:
            values.append(int(v))
        except ValueError:
            values.append(v)

    labels = None
    if args.labels:
        labels = [l.strip() for l in args.labels.split(",")]

    # Build condition factory from the template string
    condition_template = args.condition

    def condition_factory(x):
        expr = condition_template.replace("{x}", repr(x))
        return eval(f"PriorityRule.{expr}")  # noqa: S307

    tester = HypothesisTester(board=args.board, games=args.games)

    logger.info(
        "Sweeping %s on %s.%s with values %s",
        args.card,
        args.strategy,
        args.list_name,
        values,
    )

    results = tester.sweep(
        base_factory=factory,
        list_name=args.list_name,
        card_name=args.card,
        condition_factory=condition_factory,
        values=values,
        labels=labels,
    )

    # Generate report
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path("reports") / f"hypothesis_{timestamp}.html"
    else:
        output_path = args.output

    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_sweep_report(results, output_path)
    logger.info("Report written to %s", output_path)


if __name__ == "__main__":
    main()
