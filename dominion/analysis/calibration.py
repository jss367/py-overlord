"""Ground-truth calibration suite.

Each entry pairs a board with a community-known best strategy (encoded as a
hand-written strategy in ``dominion/strategy/strategies/``). The suite gives
the evolution pipeline an external reference: instead of only measuring
champions against the panel they were trained on, we can ask two questions
with well-established answers:

1. Sanity: does the known-best archetype beat Big Money on its board in this
   simulator? If not, the simulator or the strategy encoding is broken —
   evolution results on that board cannot be trusted.
2. Gap: does an evolved champion beat, tie, or lose to the known-best
   strategy? The per-board gap (percentage points of win rate below 50%)
   separates "search failure" from "policy ceiling" board by board.
"""

from __future__ import annotations

import json
import math
import random
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional, Sequence

from dominion.analysis.seed_stats import paired_t, spread, t_interval, welch

if TYPE_CHECKING:
    from dominion.strategy.enhanced_strategy import EnhancedStrategy

REPO_ROOT = Path(__file__).resolve().parents[2]
BOARDS_DIR = REPO_ROOT / "boards" / "calibration"


@dataclass(frozen=True)
class CalibrationEntry:
    """A board with a community-known best strategy."""

    key: str
    known_best: str  # display name registered in StrategyLoader
    archetype: str  # one-line description of the known-best plan
    source: str  # community reference for why this is the known answer

    def board_path(self) -> Path:
        return BOARDS_DIR / f"{self.key}.txt"


CALIBRATION_SUITE: tuple[CalibrationEntry, ...] = (
    CalibrationEntry(
        key="smithy_bm",
        known_best="Double Smithy",
        archetype="Big Money plus two Smithies, green on Duchy late",
        source="Classic simulator result (Geronimoo/Dominiate): BM+2 Smithy beats straight BM",
    ),
    CalibrationEntry(
        key="witch_bm",
        known_best="Double Witch",
        archetype="Big Money plus two Witches; curse pressure wins the mirror-free board",
        source="Community consensus: Witch-BM crushes BM on support-free boards",
    ),
    CalibrationEntry(
        key="chapel_witch",
        known_best="Chapel Witch Classic",
        archetype="Open Chapel, thin hard, one-two Witches, then money and green",
        source="Canonical Dominion opening: Chapel+Witch beats unthinned Witch money",
    ),
    CalibrationEntry(
        key="gardens_workshop",
        known_best="Gardens Workshop Rush",
        archetype="Workshops gain Gardens every turn; fatten deck and end on piles",
        source="Classic rush: Workshop/Gardens beats Big Money on weak-money boards",
    ),
    CalibrationEntry(
        key="wharf_bm",
        known_best="Big Money Wharf",
        archetype="Big Money plus two Wharves; the strongest BM+X of the classic sims",
        source="Dominiate/Councilroom era result: BM-Wharf beats BM and most BM+X",
    ),
    CalibrationEntry(
        key="rebuild_duchy",
        known_best="Rebuild Rush",
        archetype="Two Rebuilds, buy Duchies over Gold, race the Province pile",
        source="Rebuild dominated its era; Rebuild/Duchy beats money strategies outright",
    ),
    CalibrationEntry(
        key="jack_bm",
        known_best="Double Jack",
        archetype="Two Jacks of All Trades plus money; steady Silver flow and filtering",
        source="Double Jack was a famously strong benchmark strategy (Isotropic era)",
    ),
    CalibrationEntry(
        key="mountebank_bm",
        known_best="Mountebank Money",
        archetype="Big Money plus one-two Mountebanks; junk the opponent, buy points",
        source="Mountebank-BM is a standard strong baseline on support-free boards",
    ),
    CalibrationEntry(
        key="courtyard_bm",
        known_best="Courtyard Money",
        archetype="Big Money plus two Courtyards bought on 2-4 coin hands",
        source="BM-Courtyard is a classic strong BM+X (draw 3, topdeck spare card)",
    ),
    CalibrationEntry(
        key="first_game",
        known_best="First Game Smithy Militia",
        archetype="Smithy money with a Militia on the base-set First Game kingdom",
        source="Community consensus for the First Game kingdom: Smithy-BM (+Militia) wins",
    ),
)


def entries_for_keys(keys: Optional[Iterable[str]]) -> list[CalibrationEntry]:
    """Return suite entries for ``keys`` (all entries when ``keys`` is falsy)."""

    keys = list(keys) if keys is not None else None
    if not keys:
        return list(CALIBRATION_SUITE)
    by_key = {entry.key: entry for entry in CALIBRATION_SUITE}
    missing = [key for key in keys if key not in by_key]
    if missing:
        raise ValueError(f"Unknown calibration board(s): {', '.join(missing)}")
    return [by_key[key] for key in keys]


def wilson_interval(wins: int, games: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a win proportion, as (lo, hi) in [0, 1]."""

    if games <= 0:
        return (0.0, 1.0)
    p = wins / games
    z2 = z * z
    denom = 1 + z2 / games
    center = (p + z2 / (2 * games)) / denom
    margin = z * math.sqrt(p * (1 - p) / games + z2 / (4 * games * games)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def gap_points(winrate_pct: float) -> float:
    """Percentage points of win rate below parity (0 when at or above 50%)."""

    return max(0.0, 50.0 - winrate_pct)


@dataclass
class MatchOutcome:
    """Result of one head-to-head series on a calibration board."""

    board: str
    strategy_a: str
    strategy_b: str
    wins_a: int
    games: int
    # Seed of the run that produced strategy A (None for unseeded or
    # hand-written strategies). Several outcomes for one board with distinct
    # seeds are what :func:`summarize_by_board` aggregates.
    seed: Optional[int] = None

    @property
    def winrate_a(self) -> float:
        return self.wins_a / self.games * 100 if self.games else 0.0

    @property
    def ci_a(self) -> tuple[float, float]:
        lo, hi = wilson_interval(self.wins_a, self.games)
        return (lo * 100, hi * 100)

    def to_dict(self) -> dict:
        lo, hi = self.ci_a
        return {
            "board": self.board,
            "strategy_a": self.strategy_a,
            "strategy_b": self.strategy_b,
            "wins_a": self.wins_a,
            "games": self.games,
            "winrate_a": round(self.winrate_a, 2),
            "ci_a": [round(lo, 2), round(hi, 2)],
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MatchOutcome":
        return cls(
            board=data["board"],
            strategy_a=data["strategy_a"],
            strategy_b=data["strategy_b"],
            wins_a=int(data["wins_a"]),
            games=int(data["games"]),
            seed=data.get("seed"),
        )


@dataclass
class BoardSummary:
    """All seeds' outcomes for one board, with across-seed statistics.

    With one outcome the interval is that run's Wilson interval (deck luck
    within the run); with several it is a Student-t interval over the seeds'
    win rates (trajectory luck across runs), which is the spread a pipeline
    change has to clear.
    """

    board: str
    known_best: str
    outcomes: list[MatchOutcome] = field(default_factory=list)

    @property
    def seeds(self) -> int:
        return len(self.outcomes)

    @property
    def winrates(self) -> list[float]:
        return [o.winrate_a for o in self.outcomes]

    @property
    def games_per_seed(self) -> int:
        return self.outcomes[0].games if self.outcomes else 0

    @property
    def mean_winrate(self) -> float:
        return spread(self.winrates)[0]

    @property
    def stdev(self) -> float:
        return spread(self.winrates)[1]

    @property
    def ci(self) -> tuple[float, float]:
        if self.seeds == 1:
            return self.outcomes[0].ci_a
        lo, hi = t_interval(self.winrates)
        return (max(0.0, lo), min(100.0, hi))

    @property
    def gap(self) -> float:
        return gap_points(self.mean_winrate)

    @property
    def verdict(self) -> str:
        lo, hi = self.ci
        if lo > 50.0:
            return "BEATS KNOWN BEST"
        if hi < 50.0:
            return "BEHIND"
        return "TIED" if self.seeds == 1 else f"UNRESOLVED ({self.seeds} seeds)"


def summarize_by_board(outcomes: Sequence[MatchOutcome]) -> list[BoardSummary]:
    """Group outcomes by board, preserving first-seen order."""

    summaries: dict[str, BoardSummary] = {}
    for outcome in outcomes:
        summary = summaries.get(outcome.board)
        if summary is None:
            summary = BoardSummary(board=outcome.board, known_best=outcome.strategy_b)
            summaries[outcome.board] = summary
        summary.outcomes.append(outcome)
    return list(summaries.values())


def mean_gap(summaries: Sequence[BoardSummary]) -> float:
    return sum(s.gap for s in summaries) / len(summaries) if summaries else 0.0


def _sanity_verdict(outcome: MatchOutcome) -> str:
    lo, _ = outcome.ci_a
    if lo > 50.0:
        return "PASS"
    if outcome.winrate_a > 50.0:
        return "WEAK"
    return "FAIL"


def run_match(
    entry: CalibrationEntry,
    strategy_a: str,
    strategy_b: str,
    games: int,
    *,
    log_folder: str = "battle_logs/calibration",
    champion_factory=None,
    workers: int = 1,
) -> MatchOutcome:
    """Battle two registered strategies on the entry's board.

    ``champion_factory`` registers an unregistered strategy (e.g. a freshly
    evolved champion) under ``strategy_a`` before the battle runs. ``workers``
    > 1 plays the games in worker processes (0 = one per CPU).
    """

    if games <= 0:
        raise ValueError(f"games must be positive, got {games}")

    from dominion.boards.loader import load_board
    from dominion.simulation.strategy_battle import StrategyBattle

    board = load_board(entry.board_path())
    battle = StrategyBattle(board_config=board, log_folder=log_folder, workers=workers)
    if champion_factory is not None:
        battle.strategy_loader.register_strategy(strategy_a, champion_factory)
    try:
        results = battle.run_battle(strategy_a, strategy_b, games)
    finally:
        battle.close()
    return MatchOutcome(
        board=entry.key,
        strategy_a=strategy_a,
        strategy_b=strategy_b,
        wins_a=results["strategy1_wins"],
        games=games,
    )


def run_sanity(
    entries: Sequence[CalibrationEntry],
    games: int,
    baselines: Sequence[str] = ("Big Money",),
    *,
    log_folder: str = "battle_logs/calibration",
    workers: int = 1,
) -> list[MatchOutcome]:
    """Battle each entry's known-best strategy against the baseline(s)."""

    outcomes = []
    for entry in entries:
        for baseline in baselines:
            outcomes.append(
                run_match(entry, entry.known_best, baseline, games, log_folder=log_folder, workers=workers)
            )
    return outcomes


def evolve_and_evaluate(
    entry: CalibrationEntry,
    *,
    confirm_games: int = 400,
    log_folder: str = "battle_logs/calibration",
    seed: Optional[int] = None,
    **trainer_kwargs,
) -> tuple[MatchOutcome, dict, EnhancedStrategy]:
    """Evolve a champion for the entry's board and battle it vs known-best.

    ``trainer_kwargs`` are forwarded to :class:`GeneticTrainer` (population
    size, generations, games_per_eval, ...); a ``workers`` entry also drives
    the confirmation battle. ``seed`` fixes the GA's mutation stream, the
    trainer's evaluation seed block, and the confirmation battle, making the
    whole run reproducible; distinct seeds give independent trajectories for
    :func:`summarize_by_board`. Returns the champion-vs-known-best outcome,
    the trainer metadata, and the champion strategy itself (so callers can
    persist the genome for diagnosis).
    """

    from dominion.boards.loader import load_board
    from dominion.simulation.genetic_trainer import GeneticTrainer

    board = load_board(entry.board_path())
    if seed is not None:
        random.seed(seed)
        trainer_kwargs.setdefault("eval_seed", seed)
    log_suffix = f"/seed{seed}" if seed is not None else ""
    trainer = GeneticTrainer(
        kingdom_cards=board.kingdom_cards,
        board_config=board,
        log_folder=f"training_logs/calibration/{entry.key}{log_suffix}",
        **trainer_kwargs,
    )
    champion, metadata = trainer.train()
    if champion is None:
        raise RuntimeError(f"Training produced no champion for board {entry.key}")

    champion_name = f"Champion {entry.key}"
    if seed is not None:
        # The confirmation battle draws its shuffles from the global RNG;
        # re-seed so it does not depend on how many numbers training consumed.
        random.seed(seed + 1)
    outcome = run_match(
        entry,
        champion_name,
        entry.known_best,
        confirm_games,
        log_folder=log_folder,
        champion_factory=lambda: deepcopy(champion),
        workers=trainer_kwargs.get("workers", 1),
    )
    outcome.seed = seed
    return outcome, metadata, champion


def _markdown_table(header: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def render_sanity_report(outcomes: Sequence[MatchOutcome]) -> str:
    """Markdown report: does each known-best beat its baseline?"""

    rows = []
    for o in outcomes:
        lo, hi = o.ci_a
        rows.append(
            [
                o.board,
                o.strategy_a,
                o.strategy_b,
                str(o.games),
                f"{o.winrate_a:.1f}%",
                f"[{lo:.1f}%, {hi:.1f}%]",
                _sanity_verdict(o),
            ]
        )
    table = _markdown_table(
        ["Board", "Known best", "Baseline", "Games", "Win rate", "95% CI", "Verdict"],
        rows,
    )
    return "# Calibration sanity: known-best vs baseline\n\n" + table + "\n"


def render_evolve_report(outcomes: Sequence[MatchOutcome]) -> str:
    """Markdown report: evolved champion vs known-best, with per-board gap.

    Outcomes sharing a board are treated as independent seeds of the same
    run and aggregated; see :class:`BoardSummary` for which interval is
    shown. The gap is taken on the across-seed mean win rate.
    """

    summaries = summarize_by_board(outcomes)
    rows = []
    for s in summaries:
        lo, hi = s.ci
        rows.append(
            [
                s.board,
                s.known_best,
                str(s.seeds),
                str(s.games_per_seed),
                f"{s.mean_winrate:.1f}%",
                "n/a" if s.seeds == 1 else f"{s.stdev:.1f}",
                f"[{lo:.1f}%, {hi:.1f}%]",
                f"{s.gap:.1f}",
                s.verdict,
            ]
        )
    table = _markdown_table(
        [
            "Board",
            "Known best",
            "Seeds",
            "Games/seed",
            "Champion win rate",
            "Across-seed sd",
            "95% CI",
            "Gap (pp)",
            "Verdict",
        ],
        rows,
    )
    multi = any(s.seeds > 1 for s in summaries)
    behind = sum(1 for s in summaries if s.verdict == "BEHIND")
    interval_note = (
        "CI is a Student-t interval over seeds where there are several, "
        "otherwise the single run's Wilson interval."
        if multi
        else "Single seed per board: the CI reflects deck luck within the run, "
        "not trajectory luck across runs — re-run with --seeds to measure that."
    )
    return (
        "# Calibration: evolved champion vs known-best\n\n"
        + table
        + f"\n\n**Mean gap: {mean_gap(summaries):.1f} percentage points** "
        + "(0 = champions match or beat every known-best); "
        + f"behind on {behind} of {len(summaries)} boards.\n\n"
        + interval_note
        + "\n"
    )


def _fmt_p(pvalue: float) -> str:
    return "n/a" if math.isnan(pvalue) else f"{pvalue:.3f}"


def render_comparison(
    baseline: Sequence[MatchOutcome],
    candidate: Sequence[MatchOutcome],
    *,
    baseline_label: str = "baseline",
    candidate_label: str = "candidate",
) -> str:
    """Markdown: per-board Welch test of candidate vs baseline, plus suite gap.

    Each board's test uses the across-seed win rates of both arms; with one
    seed on either side it cannot be resolved and says so. The suite-level
    mean gap is compared with a paired t-test over the boards both arms ran.
    """

    base_by_board = {s.board: s for s in summarize_by_board(baseline)}
    cand_by_board = {s.board: s for s in summarize_by_board(candidate)}
    shared = [board for board in cand_by_board if board in base_by_board]

    rows = []
    for board in shared:
        b, c = base_by_board[board], cand_by_board[board]
        delta = c.mean_winrate - b.mean_winrate
        t, pvalue = welch(b.winrates, c.winrates)
        if math.isnan(t):
            verdict = "need >=2 seeds per arm"
        elif pvalue < 0.05:
            verdict = f"{candidate_label} better" if delta > 0 else f"{candidate_label} worse"
        else:
            verdict = "unresolved at this seed count"
        rows.append(
            [
                board,
                f"{b.mean_winrate:.1f}% (n={b.seeds})",
                f"{c.mean_winrate:.1f}% (n={c.seeds})",
                f"{delta:+.1f}pp",
                _fmt_p(pvalue),
                verdict,
            ]
        )
    table = _markdown_table(
        ["Board", baseline_label, candidate_label, "Delta", "Welch p", "Verdict"],
        rows,
    )

    base_gaps = [base_by_board[board].gap for board in shared]
    cand_gaps = [cand_by_board[board].gap for board in shared]
    lines = [f"# Calibration comparison: {candidate_label} vs {baseline_label}", "", table, ""]
    if shared:
        base_mean = sum(base_gaps) / len(base_gaps)
        cand_mean = sum(cand_gaps) / len(cand_gaps)
        _, pvalue = paired_t(base_gaps, cand_gaps)
        lines.append(
            f"**Mean gap over {len(shared)} shared boards: {base_mean:.1f} -> {cand_mean:.1f} pp "
            f"({cand_mean - base_mean:+.1f}); paired t over boards p = {_fmt_p(pvalue)}.**"
        )
    else:
        lines.append("No boards in common between the two reports.")
    missing = [board for board in cand_by_board if board not in base_by_board]
    if missing:
        lines.append(f"Boards only in {candidate_label}: {', '.join(missing)}.")
    lines.append("")
    return "\n".join(lines)


def save_outcomes_json(outcomes: Sequence[MatchOutcome], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([o.to_dict() for o in outcomes], indent=2) + "\n", encoding="utf-8"
    )


def load_outcomes_json(path: Path) -> list[MatchOutcome]:
    """Read outcomes written by :func:`save_outcomes_json` (any version)."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [MatchOutcome.from_dict(item) for item in payload]
