"""Run batches of Dominion games in worker processes.

The simulator is pure Python and single-threaded, so a fitness evaluation or
a head-to-head battle is bound by one core. This module farms games out to a
process pool while keeping every result identical to the serial path:

- each game is seeded explicitly (the caller derives the seed), so a game
  plays the same shuffles whichever worker runs it;
- strategies cross the process boundary with :mod:`cloudpickle`, which
  handles the lambda conditions and hand-written closures that the standard
  pickler rejects;
- workers report which priority rules fired so rule pruning sees exactly what
  it would have seen in-process.

Workers are started with the ``spawn`` context, each building one
:class:`~dominion.simulation.strategy_battle.StrategyBattle` from a
:class:`BattleSpec` and reusing it for every task.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import random
from concurrent.futures import Future, ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Optional

import cloudpickle

log = logging.getLogger(__name__)

DEFAULT_GAMES_PER_TASK = 4


def resolve_workers(workers: Optional[int]) -> int:
    """Turn a ``workers`` setting into a concrete count.

    ``None`` or ``0`` means "one per CPU"; anything below one is clamped to a
    single (serial) worker.
    """

    if workers is None or workers == 0:
        return max(1, os.cpu_count() or 1)
    return max(1, int(workers))


@dataclass(frozen=True)
class BattleSpec:
    """Everything a worker needs to rebuild the caller's ``StrategyBattle``."""

    kingdom_cards: Optional[tuple[str, ...]]
    log_folder: str
    log_frequency: int
    use_shelters: bool
    board_config: Any = None


@dataclass
class GameTask:
    """A chunk of games between one strategy and one opponent.

    ``games`` lists ``(game_num, seed)`` pairs. Even game numbers seat the
    strategy first, odd ones seat the opponent first, mirroring the serial
    seat-swap convention.
    """

    task_id: int
    strategy_blob: bytes
    opponent_blob: bytes
    kingdom_card_names: list[str]
    landscape_kwargs: dict[str, list[str]]
    games: list[tuple[int, int]]
    collect_fired: bool = False
    collect_decisions: bool = False
    strategy_label: str = ""
    opponent_label: str = ""


@dataclass
class GameResult:
    game_num: int
    won: bool
    my_score: int
    opp_score: int
    turns: int
    log_path: Optional[str] = None
    decision_firings: Optional[dict[str, Any]] = None


@dataclass
class TaskResult:
    task_id: int
    games: list[GameResult] = field(default_factory=list)
    fired: dict[str, list[int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Worker side
# ---------------------------------------------------------------------------

_WORKER_BATTLE = None


def _init_worker(spec_blob: bytes) -> None:
    """Build the worker's ``StrategyBattle`` once; every task reuses it."""

    global _WORKER_BATTLE
    from dominion.simulation.strategy_battle import StrategyBattle

    spec: BattleSpec = cloudpickle.loads(spec_blob)
    _WORKER_BATTLE = StrategyBattle(
        list(spec.kingdom_cards) if spec.kingdom_cards is not None else None,
        spec.log_folder,
        use_shelters=spec.use_shelters,
        board_config=spec.board_config,
        log_frequency=spec.log_frequency,
    )


def _fired_indices(strategy) -> dict[str, list[int]]:
    from dominion.strategy.rule_pruning import _PRIORITY_LIST_ATTRS

    fired: dict[str, list[int]] = {}
    for attr in _PRIORITY_LIST_ATTRS:
        rules = getattr(strategy, attr, None) or []
        indices = [i for i, rule in enumerate(rules) if getattr(rule, "_fired", False)]
        if indices:
            fired[attr] = indices
    return fired


def run_game_task(task: GameTask) -> TaskResult:
    """Play every game in ``task`` on this process's battle system."""

    from dominion.ai.genetic_ai import GeneticAI
    from dominion.strategy.rule_pruning import reset_fire_flags

    battle = _WORKER_BATTLE
    if battle is None:  # pragma: no cover - only when called outside a pool
        raise RuntimeError("run_game_task called in a process without _init_worker")

    strategy = cloudpickle.loads(task.strategy_blob)
    opponent = cloudpickle.loads(task.opponent_blob)
    if task.collect_fired:
        reset_fire_flags(strategy)

    result = TaskResult(task_id=task.task_id)
    for game_num, seed in task.games:
        random.seed(seed)
        ai_me = GeneticAI(strategy)
        ai_opp = GeneticAI(opponent)
        decision_stats = None
        firings = None
        if task.collect_decisions:
            firings = {
                "strategy1": battle._empty_decision_firings(task.strategy_label),
                "strategy2": battle._empty_decision_firings(task.opponent_label),
            }
            decision_stats = {ai_me: firings["strategy1"], ai_opp: firings["strategy2"]}
        seats = (ai_me, ai_opp) if game_num % 2 == 0 else (ai_opp, ai_me)
        winner, scores, log_path, turns = battle.run_game(
            seats[0],
            seats[1],
            task.kingdom_card_names,
            decision_stats_by_ai=decision_stats,
            **task.landscape_kwargs,
        )
        result.games.append(
            GameResult(
                game_num=game_num,
                won=winner == ai_me,
                my_score=scores.get(ai_me.name, 0) if scores else 0,
                opp_score=scores.get(ai_opp.name, 0) if scores else 0,
                turns=turns,
                log_path=log_path,
                decision_firings=firings,
            )
        )
    if task.collect_fired:
        result.fired = _fired_indices(strategy)
    return result


# ---------------------------------------------------------------------------
# Caller side
# ---------------------------------------------------------------------------


def chunk_games(games: list[tuple[int, int]], games_per_task: int) -> list[list[tuple[int, int]]]:
    size = max(1, int(games_per_task))
    return [games[i : i + size] for i in range(0, len(games), size)]


class GamePool:
    """A lazily started process pool bound to one :class:`BattleSpec`."""

    def __init__(self, workers: int, spec: BattleSpec):
        self.workers = resolve_workers(workers)
        self.spec = spec
        self._executor: Optional[ProcessPoolExecutor] = None

    def _ensure_started(self) -> ProcessPoolExecutor:
        if self._executor is None:
            ctx = mp.get_context("spawn")
            self._executor = ProcessPoolExecutor(
                max_workers=self.workers,
                mp_context=ctx,
                initializer=_init_worker,
                initargs=(cloudpickle.dumps(self.spec),),
            )
            log.info("Started %d game worker%s", self.workers, "s" if self.workers != 1 else "")
        return self._executor

    def run(self, tasks: list[GameTask]) -> dict[int, TaskResult | BaseException]:
        """Run every task; map ``task_id`` to its result or the exception it raised."""

        if not tasks:
            return {}
        executor = self._ensure_started()
        futures: dict[int, Future] = {task.task_id: executor.submit(run_game_task, task) for task in tasks}
        results: dict[int, TaskResult | BaseException] = {}
        for task_id, future in futures.items():
            try:
                results[task_id] = future.result()
            except Exception as exc:  # noqa: BLE001 - reported per task by the caller
                results[task_id] = exc
        return results

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None

    def __enter__(self) -> "GamePool":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
