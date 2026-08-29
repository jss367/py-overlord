"""Double-oracle style search: evolve best responses against a maintained pool.

The fixed-panel objective is the binding constraint on this search. Two
independent diagnoses agree:

* the BM+X calibration boards (smithy_bm, witch_bm, wharf_bm) stay BEHIND
  their community-known best because a Big-Money panel gives no gradient
  toward mirror-optimal play;
* on Oslo, evolving *from* the winning engine topology against the weak panel
  drifted away from it (34.8% / 18.2% against the previous champions) — the
  search was not punished for abandoning a strictly better strategy, because
  nothing in the panel could exploit the abandonment.

This script closes that loop. Each round evolves a best response against the
current opponent pool, then promotes that champion into the pool, so the next
round has to beat everything the search has already found. Fitness is
aggregated with worst-case pressure (see
:mod:`dominion.simulation.adversarial_league`), which is what stops a
candidate from banking a good mean by farming the weakest member.

Usage::

    PYTHONPATH=. python scripts/league_evolve.py --board boards/oslo.txt \\
        --rounds 3 --generations 20 --population 30 --games-per-eval 20 \\
        --compare "Oslo Workers Village Magnate Engine" \\
        --compare "Oslo Workers Village Magnate Refined Engine"

The ``--compare`` strategies are the gate: a league champion should hold its
own against reference strategies the old pipeline drifted away from.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from copy import deepcopy
from pathlib import Path
from typing import Optional

from dominion.analysis.calibration import wilson_interval
from dominion.analysis.engine_archetypes import build_engine_seeds
from dominion.boards.loader import BoardConfig, load_board
from dominion.simulation.adversarial_league import (
    ORIGIN_CHAMPION,
    AdversarialLeague,
    build_seeded_league,
)
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.strategies.base_strategy import BaseStrategy

log = logging.getLogger("league_evolve")


def head_to_head(
    board: BoardConfig,
    name_a: str,
    strategy_a: Optional[BaseStrategy],
    name_b: str,
    strategy_b: Optional[BaseStrategy],
    games: int,
    *,
    log_folder: str = "battle_logs/league",
) -> dict:
    """Battle two strategies on ``board`` and return A's record.

    Either side may be ``None``, meaning "resolve this name through the
    strategy loader" — that is how registered reference strategies (the
    ``--compare`` gate) are faced without copying them into the pool.
    """

    battle = StrategyBattle(board_config=board, log_folder=log_folder)
    if strategy_a is not None:
        battle.strategy_loader.register_strategy(name_a, lambda s=strategy_a: deepcopy(s))
    if strategy_b is not None:
        battle.strategy_loader.register_strategy(name_b, lambda s=strategy_b: deepcopy(s))

    results = battle.run_battle(name_a, name_b, games)
    wins = results["strategy1_wins"]
    low, high = wilson_interval(wins, games)
    return {
        "opponent": name_b,
        "games": games,
        "wins": wins,
        "win_rate": wins / games * 100.0,
        "ci": [low * 100.0, high * 100.0],
    }


def build_league(
    board: BoardConfig,
    *,
    capacity: int,
    max_engines: int,
    loader,
    reference_names: list[str],
) -> AdversarialLeague:
    """Seed the pool with named reference strategies, then engine archetypes.

    References go first: a strategy someone has already shown to be strong on
    this board is the sharpest thing the pool can hold, and the enumerated
    engines fill whatever capacity is left.
    """

    extra: list[tuple[str, BaseStrategy]] = []
    for name in reference_names:
        strategy = loader.get_strategy(name)
        if strategy is None:
            log.warning("Reference strategy %r not found in the loader; skipping", name)
            continue
        extra.append((name, strategy))

    league = build_seeded_league(
        board, capacity=capacity, max_engines=max_engines, extra=extra
    )
    log.info(
        "League seeded with %d member%s: %s",
        len(league),
        "s" if len(league) != 1 else "",
        ", ".join(m.name for m in league.members),
    )
    return league


def run_rounds(
    board: BoardConfig,
    league: Optional[AdversarialLeague],
    *,
    rounds: int,
    worst_case_weight: float,
    inject_engine_seeds: bool,
    max_engines: int,
    eval_seed: Optional[int],
    trainer_kwargs: dict,
) -> tuple[list[dict], list[BaseStrategy]]:
    """Evolve one best response per round, promoting each into the pool.

    ``league=None`` is the control arm: the trainer falls back to its hall of
    fame and (with ``worst_case_weight=0``) to mean aggregation, i.e. exactly
    the pipeline that drifted. Everything else — board, budget, seeds, RNG —
    is held fixed, so the gate difference is attributable to the league.
    """

    seeds = build_engine_seeds(board, max_engines=max_engines) if inject_engine_seeds else []
    round_reports: list[dict] = []
    champions: list[BaseStrategy] = []

    for round_index in range(rounds):
        pool_size = len(league) if league is not None else 0
        log.info(
            "=== Round %d/%d — pool has %d member%s ===",
            round_index + 1,
            rounds,
            pool_size,
            "s" if pool_size != 1 else "",
        )
        trainer = GeneticTrainer(
            kingdom_cards=board.kingdom_cards,
            board_config=board,
            league=league,
            worst_case_weight=worst_case_weight,
            default_baseline_panel=True,
            # Each round gets its own seed block so rounds do not all evaluate
            # on the same shuffles, while remaining reproducible from --seed.
            eval_seed=None if eval_seed is None else eval_seed + round_index,
            log_folder=f"training_logs/league/round{round_index + 1}",
            **trainer_kwargs,
        )
        # Round 1 starts from the assembled engines: composing one is the
        # fitness valley the archetype seeds exist to skip. Later rounds start
        # from the pool's own champions via the same injection path.
        if round_index == 0 and seeds:
            trainer.inject_strategies([deepcopy(s) for _, s in seeds])

        champion, metadata = trainer.train()
        if champion is None:
            log.warning("Round %d produced no champion; stopping", round_index + 1)
            break

        champions.append(champion)
        breakdown = list(trainer.best_eval_breakdown)
        if league is None:
            added, dropped = False, []
        else:
            league.record_champion_results(breakdown)
            added = league.add(
                champion, name=f"BestResponse-r{round_index + 1}", origin=ORIGIN_CHAMPION
            )
            dropped = league.prune() if added else []

        round_reports.append(
            {
                "round": round_index + 1,
                "champion_added": added,
                "champion_fitness": metadata.get("fitness"),
                "champion_win_rate": metadata.get("win_rate"),
                "breakdown": [list(entry) for entry in breakdown],
                "dropped": [m.name for m in dropped],
                "league": league.summary() if league is not None else [],
                "champion": _describe(champion),
            }
        )
        if league is not None and not added:
            log.info(
                "Round %d re-derived a pool member; the search has converged "
                "against the current pool",
                round_index + 1,
            )

    return round_reports, champions


def _describe(strategy: BaseStrategy) -> dict:
    """Capture enough of a genome to reconstruct what the champion did."""

    def rules(attr):
        return [
            {
                "card": rule.card_name,
                "condition": getattr(getattr(rule, "condition", None), "_source", None),
            }
            for rule in getattr(strategy, attr, []) or []
        ]

    return {
        "name": strategy.name,
        "gain_priority": rules("gain_priority"),
        "action_priority": rules("action_priority"),
        "treasure_priority": rules("treasure_priority"),
        "trash_priority": rules("trash_priority"),
    }


def run_gate(
    board: BoardConfig,
    champion: BaseStrategy,
    compare_names: list[str],
    games: int,
) -> list[dict]:
    """Battle the final champion against each reference strategy."""

    results = []
    for name in compare_names:
        log.info("Gate: champion vs %s (%d games)", name, games)
        results.append(
            head_to_head(board, "LeagueChampion", champion, name, None, games)
        )
    return results


def render_report(payload: dict) -> str:
    """Render the run as markdown."""

    lines = [
        f"# Adversarial league: {payload['board']} ({payload['arm']} arm)",
        "",
        f"Rounds: {payload['rounds']} | worst-case weight: {payload['worst_case_weight']} "
        f"| pool capacity: {payload['capacity']}",
        "",
    ]
    if payload["final_league"]:
        lines += [
            "## Final pool",
            "",
            "| Member | Origin | Champion win rate |",
            "|---|---|---|",
        ]
        for member in payload["final_league"]:
            rate = member["champion_win_rate"]
            rate_text = "—" if rate is None else f"{rate:.1f}%"
            lines.append(f"| {member['name']} | {member['origin']} | {rate_text} |")
    else:
        lines.append("Control arm: hall of fame, mean aggregation, no seeded pool.")

    if payload["gate"]:
        lines += [
            "",
            "## Gate: final champion vs reference strategies",
            "",
            "| Opponent | Games | Champion win rate | 95% CI |",
            "|---|---|---|---|",
        ]
        for row in payload["gate"]:
            lines.append(
                f"| {row['opponent']} | {row['games']} | {row['win_rate']:.1f}% | "
                f"[{row['ci'][0]:.1f}%, {row['ci'][1]:.1f}%] |"
            )

    lines += ["", "## Rounds", ""]
    for report in payload["round_reports"]:
        lines.append(
            f"- Round {report['round']}: fitness "
            + ("n/a" if report["champion_fitness"] is None else f"{report['champion_fitness']:.2f}")
            + (
                ""
                if not payload["final_league"]
                else ", champion joined the pool"
                if report["champion_added"]
                else ", champion duplicated a pool member"
            )
            + (f", dropped {', '.join(report['dropped'])}" if report["dropped"] else "")
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--board", type=Path, required=True, help="Board definition file")
    parser.add_argument("--rounds", type=int, default=3, help="Best-response rounds")
    parser.add_argument("--capacity", type=int, default=6, help="Opponent pool size")
    parser.add_argument("--max-engines", type=int, default=3, help="Engine archetypes to seed")
    parser.add_argument(
        "--worst-case-weight",
        type=float,
        default=0.5,
        help="0 = mean over the panel (legacy), 1 = score purely on the worst matchups",
    )
    parser.add_argument(
        "--reference",
        action="append",
        default=[],
        help="Registered strategy to seed into the pool. Repeatable.",
    )
    parser.add_argument(
        "--compare",
        action="append",
        default=[],
        help="Registered strategy to battle the final champion against. Repeatable.",
    )
    parser.add_argument("--gate-games", type=int, default=200)
    parser.add_argument("--population", type=int, default=30)
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--games-per-eval", type=int, default=20)
    parser.add_argument("--mutation-rate", type=float, default=0.1)
    parser.add_argument(
        "--control",
        action="store_true",
        help=(
            "Control arm: train against the hall of fame with mean aggregation "
            "(the pipeline that drifted), holding every other setting fixed"
        ),
    )
    parser.add_argument(
        "--no-engine-seeds",
        action="store_true",
        help="Do not inject the engine archetypes into the starting population",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed the RNG and the evaluation seed block, making the run reproducible",
    )
    parser.add_argument("--output", type=Path, default=None, help="JSON report path")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    board = load_board(args.board)
    league: Optional[AdversarialLeague] = None
    if not args.control:
        probe = StrategyBattle(board_config=board, log_folder="battle_logs/league/_probe")
        league = build_league(
            board,
            capacity=args.capacity,
            max_engines=args.max_engines,
            loader=probe.strategy_loader,
            reference_names=args.reference,
        )
        if not len(league):
            raise SystemExit(
                "League is empty: the board yielded no engine archetypes and no "
                "--reference strategies resolved. Nothing to train against."
            )

    round_reports, champions = run_rounds(
        board,
        league,
        rounds=args.rounds,
        worst_case_weight=0.0 if args.control else args.worst_case_weight,
        inject_engine_seeds=not args.no_engine_seeds,
        max_engines=args.max_engines,
        eval_seed=args.seed,
        trainer_kwargs={
            "population_size": args.population,
            "generations": args.generations,
            "games_per_eval": args.games_per_eval,
            "mutation_rate": args.mutation_rate,
        },
    )
    if not round_reports:
        raise SystemExit("No round produced a champion")

    final_champion = champions[-1] if champions else None
    gate: list[dict] = []
    if final_champion is not None and args.compare:
        gate = run_gate(board, final_champion, args.compare, args.gate_games)

    payload = {
        "board": args.board.stem,
        "arm": "control" if args.control else "league",
        "rounds": args.rounds,
        "capacity": args.capacity,
        "worst_case_weight": 0.0 if args.control else args.worst_case_weight,
        "seed": args.seed,
        "final_league": league.summary() if league is not None else [],
        "round_reports": round_reports,
        "gate": gate,
    }

    output = args.output or Path("reports/league") / f"{args.board.stem}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    markdown = output.with_suffix(".md")
    markdown.write_text(render_report(payload), encoding="utf-8")

    print(render_report(payload))
    print(f"Wrote {output} and {markdown}")


if __name__ == "__main__":
    main()
