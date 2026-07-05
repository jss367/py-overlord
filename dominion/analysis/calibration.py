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
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

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
        }


def _sanity_verdict(outcome: MatchOutcome) -> str:
    lo, _ = outcome.ci_a
    if lo > 50.0:
        return "PASS"
    if outcome.winrate_a > 50.0:
        return "WEAK"
    return "FAIL"


def _evolve_verdict(outcome: MatchOutcome) -> str:
    lo, hi = outcome.ci_a
    if lo > 50.0:
        return "BEATS KNOWN BEST"
    if hi < 50.0:
        return "BEHIND"
    return "TIED"


def run_match(
    entry: CalibrationEntry,
    strategy_a: str,
    strategy_b: str,
    games: int,
    *,
    log_folder: str = "battle_logs/calibration",
    champion_factory=None,
) -> MatchOutcome:
    """Battle two registered strategies on the entry's board.

    ``champion_factory`` registers an unregistered strategy (e.g. a freshly
    evolved champion) under ``strategy_a`` before the battle runs.
    """

    from dominion.boards.loader import load_board
    from dominion.simulation.strategy_battle import StrategyBattle

    board = load_board(entry.board_path())
    battle = StrategyBattle(board_config=board, log_folder=log_folder)
    if champion_factory is not None:
        battle.strategy_loader.register_strategy(strategy_a, champion_factory)
    results = battle.run_battle(strategy_a, strategy_b, games)
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
) -> list[MatchOutcome]:
    """Battle each entry's known-best strategy against the baseline(s)."""

    outcomes = []
    for entry in entries:
        for baseline in baselines:
            outcomes.append(
                run_match(entry, entry.known_best, baseline, games, log_folder=log_folder)
            )
    return outcomes


def evolve_and_evaluate(
    entry: CalibrationEntry,
    *,
    confirm_games: int = 400,
    log_folder: str = "battle_logs/calibration",
    **trainer_kwargs,
) -> tuple[MatchOutcome, dict, "EnhancedStrategy"]:
    """Evolve a champion for the entry's board and battle it vs known-best.

    ``trainer_kwargs`` are forwarded to :class:`GeneticTrainer` (population
    size, generations, games_per_eval, ...). Returns the champion-vs-known-best
    outcome, the trainer metadata, and the champion strategy itself (so
    callers can persist the genome for diagnosis).
    """

    from dominion.boards.loader import load_board
    from dominion.simulation.genetic_trainer import GeneticTrainer

    board = load_board(entry.board_path())
    trainer = GeneticTrainer(
        kingdom_cards=board.kingdom_cards,
        board_config=board,
        log_folder=f"training_logs/calibration/{entry.key}",
        **trainer_kwargs,
    )
    champion, metadata = trainer.train()
    if champion is None:
        raise RuntimeError(f"Training produced no champion for board {entry.key}")

    champion_name = f"Champion {entry.key}"
    outcome = run_match(
        entry,
        champion_name,
        entry.known_best,
        confirm_games,
        log_folder=log_folder,
        champion_factory=lambda: deepcopy(champion),
    )
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
    """Markdown report: evolved champion vs known-best, with per-board gap."""

    rows = []
    gaps = []
    for o in outcomes:
        lo, hi = o.ci_a
        gap = gap_points(o.winrate_a)
        gaps.append(gap)
        rows.append(
            [
                o.board,
                o.strategy_b,
                str(o.games),
                f"{o.winrate_a:.1f}%",
                f"[{lo:.1f}%, {hi:.1f}%]",
                f"{gap:.1f}",
                _evolve_verdict(o),
            ]
        )
    table = _markdown_table(
        ["Board", "Known best", "Games", "Champion win rate", "95% CI", "Gap (pp)", "Verdict"],
        rows,
    )
    mean_gap = sum(gaps) / len(gaps) if gaps else 0.0
    return (
        "# Calibration: evolved champion vs known-best\n\n"
        + table
        + f"\n\n**Mean gap: {mean_gap:.1f} percentage points** "
        + "(0 = champions match or beat every known-best)\n"
    )


def save_outcomes_json(outcomes: Sequence[MatchOutcome], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([o.to_dict() for o in outcomes], indent=2) + "\n", encoding="utf-8"
    )
