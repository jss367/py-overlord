"""A maintained pool of opponents that the search has to stay honest against.

The hall of fame already appends past champions to the fitness panel, but it
is not enough to fix the objective failure documented on the calibration
boards and again on Oslo. Three properties break it:

1. **Mean aggregation has no worst-case pressure.** Fitness is the mean of the
   per-opponent win rates, so a candidate that crushes Big Money 70% and loses
   to the sharp opponent 40% scores 55 — beating a mirror-optimal strategy
   that goes 55/50 for 52.5. The search is therefore *rewarded* for
   specialising against the weakest panel member. On the BM+X calibration
   boards (smithy_bm, witch_bm, wharf_bm) that is exactly the observed
   failure: champions beat plain Big Money and lose to Double Smithy.
2. **FIFO retention keeps the wrong members.** ``hall_of_fame[-size:]`` keeps
   the most *recent* champions. A drifting lineage therefore fills the pool
   with variations on its own drift, and the pool stops disagreeing with the
   population — which is the only thing that made it useful.
3. **The pool only ever contains this run's own champions.** It never contains
   the board's assembled engine archetypes, so on Oslo the pool never held the
   winning topology and drifting away from it cost the champion nothing.

This module addresses all three: the pool is *seeded* with strong reference
opponents (engine archetypes, library strategies), retention keeps the members
that are *hardest* for the current champion rather than the newest, and
:func:`aggregate_fitness` provides the worst-case-sensitive aggregation the
trainer uses in place of a plain mean.

Public API: :class:`AdversarialLeague`, :func:`aggregate_fitness`,
:func:`build_seeded_league`.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Iterable, Optional

from dominion.boards.loader import BoardConfig
from dominion.strategy.strategies.base_strategy import BaseStrategy

log = logging.getLogger(__name__)


# Origin tags. ``SEED`` members come from outside the run (engine archetypes,
# library strategies, hand-written references) and are what stop a run from
# drifting somewhere the search cannot be punished for. ``CHAMPION`` members
# are best responses the run itself produced.
ORIGIN_SEED = "seed"
ORIGIN_CHAMPION = "champion"


def _cvar_worst(values: list[float], fraction: float) -> float:
    """Mean of the worst ``fraction`` of ``values`` (a CVaR / expected
    shortfall).

    Pure ``min`` would be the textbook maximin objective, but at screening
    budget it is mostly noise: ``games_per_eval`` split across a six-member
    pool is three games per opponent, and the minimum of six three-game
    estimates tracks deck luck more than skill. Averaging the worst tail keeps
    the worst-case pressure while spending the same games on a lower-variance
    statistic.
    """

    if not values:
        return 0.0
    ordered = sorted(values)
    count = max(1, round(len(ordered) * fraction))
    return sum(ordered[:count]) / count


def aggregate_fitness(
    values: list[float], *, worst_case_weight: float, worst_fraction: float = 0.5
) -> float:
    """Blend the mean of ``values`` with their worst-case tail.

    ``worst_case_weight`` of 0 reproduces the historical plain mean; 1 scores
    purely on the worst tail. Intermediate values keep some reward for broad
    strength (a strategy that only ever draws its worst matchup is not what we
    want either) while making the hardest opponent matter.
    """

    if not values:
        return 0.0
    mean = sum(values) / len(values)
    if worst_case_weight <= 0.0:
        return mean
    worst = _cvar_worst(values, worst_fraction)
    if worst_case_weight >= 1.0:
        return worst
    return (1.0 - worst_case_weight) * mean + worst_case_weight * worst


@dataclass
class LeagueMember:
    """One opponent in the pool, with the record used to retain or drop it."""

    name: str
    strategy: BaseStrategy
    origin: str
    signature: tuple
    # Champion win rate (0-100) against this member the last time it was
    # measured. ``None`` until the member has been faced. Unmeasured members
    # are never dropped — we have no evidence they are easy.
    last_champion_win_rate: Optional[float] = None

    @property
    def difficulty(self) -> float:
        """How much gradient this member supplies, higher = harder.

        An opponent the champion beats 90% of the time teaches the search
        almost nothing; one that holds it to 40% is the entire signal.
        Unmeasured members sort as maximally hard so a member is never
        evicted before it has been faced.
        """

        if self.last_champion_win_rate is None:
            return float("inf")
        return -self.last_champion_win_rate


@dataclass
class AdversarialLeague:
    """A capacity-bounded opponent pool with difficulty-based retention."""

    capacity: int = 6
    members: list[LeagueMember] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("league capacity must be at least 1")

    # -- construction -----------------------------------------------------

    def add(self, strategy: BaseStrategy, *, name: str, origin: str) -> bool:
        """Add a copy of ``strategy`` under ``name``. Returns False if a
        structurally identical member is already present.

        The pool is deduped by genome signature rather than by name because
        the interesting duplicate is a champion that re-derives a member the
        pool already holds — it would otherwise consume a slot while adding no
        disagreement.

        ``name`` is uniquified if taken. Distinct members must not share a
        name: :meth:`record_champion_results` matches breakdown entries by
        name, so a collision silently assigns one member's win rate to
        another and corrupts the retention decision. Callers cannot guarantee
        uniqueness on their own — a trainer promoting its champion at
        generation 10 of every round proposes ``League-g10`` each time — so
        the invariant is enforced here.
        """

        signature = genome_signature(strategy)
        if any(member.signature == signature for member in self.members):
            return False

        member = deepcopy(strategy)
        member.name = self._unique_name(name)
        self.members.append(
            LeagueMember(
                name=member.name, strategy=member, origin=origin, signature=signature
            )
        )
        return True

    def _unique_name(self, name: str) -> str:
        """Return ``name``, suffixed if a member already uses it."""

        taken = {member.name for member in self.members}
        if name not in taken:
            return name
        for suffix in range(2, len(taken) + 3):
            candidate = f"{name} ({suffix})"
            if candidate not in taken:
                return candidate
        raise AssertionError("unreachable: more suffixes tried than members")

    def strategies(self) -> list[BaseStrategy]:
        """Return the pool's strategies, for extending a fitness panel."""

        return [member.strategy for member in self.members]

    def __len__(self) -> int:
        return len(self.members)

    # -- maintenance ------------------------------------------------------

    def record_champion_results(self, breakdown: Iterable[tuple]) -> None:
        """Update per-member difficulty from a champion evaluation breakdown.

        ``breakdown`` entries are the trainer's ``(opponent_name, win_rate,
        ...)`` tuples, covering the whole panel; entries that do not name a
        pool member are ignored. Member names are unique within the pool (see
        :meth:`add` callers), so matching by name is unambiguous.
        """

        rates = {entry[0]: entry[1] for entry in breakdown if len(entry) >= 2}
        for member in self.members:
            if member.name in rates:
                member.last_champion_win_rate = float(rates[member.name])

    def prune(self) -> list[LeagueMember]:
        """Drop the easiest members until the pool fits ``capacity``.

        Returns the dropped members. Retention is by difficulty, not recency:
        the member the champion beats most convincingly is the one whose slot
        is worth reusing. Seeds and champions compete on equal terms — a seed
        the search has comprehensively solved is dead weight, and keeping it
        pinned would just shrink the effective pool.
        """

        dropped: list[LeagueMember] = []
        while len(self.members) > self.capacity:
            easiest = min(self.members, key=lambda m: m.difficulty)
            self.members.remove(easiest)
            dropped.append(easiest)
            log.info(
                "League dropped %s (champion win rate %.1f%%) — pool at %d/%d",
                easiest.name,
                easiest.last_champion_win_rate if easiest.last_champion_win_rate is not None else float("nan"),
                len(self.members),
                self.capacity,
            )
        return dropped

    def hardest(self) -> Optional[LeagueMember]:
        """Return the member the champion scores worst against, if measured."""

        measured = [m for m in self.members if m.last_champion_win_rate is not None]
        if not measured:
            return None
        return min(measured, key=lambda m: m.last_champion_win_rate)

    def summary(self) -> list[dict]:
        """Serialisable snapshot of the pool, for run reports."""

        return [
            {
                "name": member.name,
                "origin": member.origin,
                "champion_win_rate": member.last_champion_win_rate,
            }
            for member in self.members
        ]


def genome_signature(strategy: BaseStrategy) -> tuple:
    """Structural fingerprint of a genome: every rule's card and condition
    source, in order.

    Mirrors ``GeneticTrainer._genome_signature``; kept here so the league has
    no dependency on the trainer (the trainer imports the league, not the
    other way round).
    """

    def rule_sig(rules) -> tuple:
        return tuple(
            (r.card_name, getattr(getattr(r, "condition", None), "_source", None))
            for r in rules or []
        )

    way_sig = tuple(
        (r.card_name, r.way_name, getattr(getattr(r, "condition", None), "_source", None))
        for r in getattr(strategy, "way_policy", []) or []
    )
    return (
        rule_sig(getattr(strategy, "gain_priority", [])),
        rule_sig(getattr(strategy, "action_priority", [])),
        rule_sig(getattr(strategy, "treasure_priority", [])),
        rule_sig(getattr(strategy, "trash_priority", [])),
        rule_sig(getattr(strategy, "bounty_hunter_exile_priority", [])),
        way_sig,
    )


def build_seeded_league(
    board: BoardConfig,
    *,
    capacity: int = 6,
    max_engines: int = 3,
    extra: Iterable[tuple[str, BaseStrategy]] = (),
) -> AdversarialLeague:
    """Build a league pre-loaded with the board's assembled engine archetypes.

    The engine seeds are the point: they are the reference topologies a run
    must not be allowed to drift away from unpunished. ``extra`` adds further
    named opponents (library strategies, hand-written references) ahead of the
    engines, and members are added until ``capacity`` is reached.
    """

    from dominion.analysis.engine_archetypes import build_engine_seeds

    league = AdversarialLeague(capacity=capacity)
    for name, strategy in extra:
        if len(league) >= capacity:
            break
        league.add(strategy, name=name, origin=ORIGIN_SEED)

    for name, strategy in build_engine_seeds(board, max_engines=max_engines):
        if len(league) >= capacity:
            break
        league.add(strategy, name=f"Seed {name}", origin=ORIGIN_SEED)

    return league
