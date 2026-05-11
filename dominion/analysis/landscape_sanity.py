"""Compare strategy results with and without board landscape pieces.

This module is intended as a quick sanity check for board-specific strategies:
if a strategy claims support for a board with an Event, Project, or Way, removing
that piece should usually change the strategy's results. A near-zero delta is a
signal that the strategy may be ignoring the landscape.

Example:

    python -m dominion.analysis.landscape_sanity \
        --strategy VictoriaEngine \
        --board boards/victoria_kingdom.txt \
        --games 500
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import BoardConfig, load_board
from dominion.simulation.strategy_battle import StrategyBattle


DEFAULT_OPPONENT = "Big Money"
DEFAULT_SEED = 1729
DEFAULT_THRESHOLD = 2.0


@dataclass(frozen=True, slots=True)
class LandscapePiece:
    """A single landscape piece declared by a board file."""

    kind: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.kind}: {self.name}"


@dataclass(frozen=True, slots=True)
class MatchupStats:
    """Aggregate results for one seeded matchup run."""

    games: int
    wins: int
    win_rate: float
    avg_score: float


@dataclass(frozen=True, slots=True)
class LandscapeSanityResult:
    """With/without comparison for one landscape piece."""

    piece: LandscapePiece
    with_piece: MatchupStats
    without_piece: MatchupStats
    threshold: float

    @property
    def win_rate_delta(self) -> float:
        return self.with_piece.win_rate - self.without_piece.win_rate

    @property
    def avg_score_delta(self) -> float:
        return self.with_piece.avg_score - self.without_piece.avg_score

    @property
    def ignores_landscape(self) -> bool:
        return abs(self.win_rate_delta) < self.threshold

    @property
    def status(self) -> str:
        if self.ignores_landscape:
            return "ignores landscape"
        return "uses landscape"


def landscape_pieces(board: BoardConfig) -> list[LandscapePiece]:
    """Return Events, Projects, and Ways declared by ``board``."""

    pieces: list[LandscapePiece] = []
    pieces.extend(LandscapePiece("Event", name) for name in board.events)
    pieces.extend(LandscapePiece("Project", name) for name in board.projects)
    pieces.extend(LandscapePiece("Way", name) for name in board.ways)
    return pieces


def without_landscape_piece(board: BoardConfig, piece: LandscapePiece) -> BoardConfig:
    """Return a copy of ``board`` with exactly ``piece`` removed."""

    events = list(board.events)
    projects = list(board.projects)
    ways = list(board.ways)

    if piece.kind == "Event":
        events.remove(piece.name)
    elif piece.kind == "Project":
        projects.remove(piece.name)
    elif piece.kind == "Way":
        ways.remove(piece.name)
    else:
        raise ValueError(f"Unsupported landscape kind: {piece.kind}")

    return BoardConfig(
        kingdom_cards=list(board.kingdom_cards),
        events=events,
        projects=projects,
        ways=ways,
        landmarks=list(board.landmarks),
        allies=list(board.allies),
        traits=dict(board.traits),
    )


def run_seeded_matchup(
    strategy_name: str,
    opponent_name: str,
    board: BoardConfig,
    games: int,
    *,
    seed: int = DEFAULT_SEED,
    use_shelters: bool = False,
) -> MatchupStats:
    """Run ``games`` with deterministic per-game seeds and return target stats."""

    if games <= 0:
        raise ValueError("games must be positive")

    battle = StrategyBattle(
        board_config=board,
        use_shelters=use_shelters,
        log_frequency=0,
    )

    if battle.strategy_loader.get_strategy(strategy_name) is None:
        raise ValueError(f"Could not find strategy: {strategy_name}")
    if battle.strategy_loader.get_strategy(opponent_name) is None:
        raise ValueError(f"Could not find opponent strategy: {opponent_name}")

    wins = 0
    total_score = 0
    kingdom_cards = list(board.kingdom_cards)

    for game_num in range(games):
        random.seed(seed + game_num)

        strategy = battle.strategy_loader.get_strategy(strategy_name)
        opponent = battle.strategy_loader.get_strategy(opponent_name)
        if strategy is None or opponent is None:
            raise RuntimeError("Strategy lookup failed after initial validation")

        strategy_ai = GeneticAI(strategy)
        opponent_ai = GeneticAI(opponent)

        if game_num % 2 == 0:
            winner, scores, *_ = battle.run_game(strategy_ai, opponent_ai, kingdom_cards)
        else:
            winner, scores, *_ = battle.run_game(opponent_ai, strategy_ai, kingdom_cards)

        wins += int(winner == strategy_ai)
        total_score += scores[strategy_ai.name]

    return MatchupStats(
        games=games,
        wins=wins,
        win_rate=wins / games * 100,
        avg_score=total_score / games,
    )


def analyze_landscapes(
    strategy_name: str,
    board: BoardConfig,
    *,
    opponent_name: str = DEFAULT_OPPONENT,
    games: int = 100,
    seed: int = DEFAULT_SEED,
    threshold: float = DEFAULT_THRESHOLD,
    use_shelters: bool = False,
) -> list[LandscapeSanityResult]:
    """Compare full-board results with each landscape piece individually stripped."""

    pieces = landscape_pieces(board)
    if not pieces:
        return []

    with_all = run_seeded_matchup(
        strategy_name,
        opponent_name,
        board,
        games,
        seed=seed,
        use_shelters=use_shelters,
    )

    results: list[LandscapeSanityResult] = []
    for piece in pieces:
        stripped_board = without_landscape_piece(board, piece)
        without_piece = run_seeded_matchup(
            strategy_name,
            opponent_name,
            stripped_board,
            games,
            seed=seed,
            use_shelters=use_shelters,
        )
        results.append(
            LandscapeSanityResult(
                piece=piece,
                with_piece=with_all,
                without_piece=without_piece,
                threshold=threshold,
            )
        )

    return results


def _format_pct(value: float, *, signed: bool = False) -> str:
    if signed:
        return f"{value:+.1f}%"
    return f"{value:.1f}%"


def _format_num(value: float, *, signed: bool = False) -> str:
    if signed:
        return f"{value:+.1f}"
    return f"{value:.1f}"


def render_table(results: Sequence[LandscapeSanityResult]) -> str:
    """Render results as a fixed-width plain-text table."""

    if not results:
        return "No Events, Projects, or Ways found on this board."

    rows = [
        [
            "Piece",
            "With WR",
            "Without WR",
            "Delta WR",
            "With Avg",
            "Without Avg",
            "Delta Avg",
            "Status",
        ]
    ]
    for result in results:
        rows.append(
            [
                result.piece.label,
                _format_pct(result.with_piece.win_rate),
                _format_pct(result.without_piece.win_rate),
                _format_pct(result.win_rate_delta, signed=True),
                _format_num(result.with_piece.avg_score),
                _format_num(result.without_piece.avg_score),
                _format_num(result.avg_score_delta, signed=True),
                result.status,
            ]
        )

    widths = [max(len(row[idx]) for row in rows) for idx in range(len(rows[0]))]
    lines: list[str] = []
    for row_idx, row in enumerate(rows):
        lines.append("  ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)))
        if row_idx == 0:
            lines.append("  ".join("-" * width for width in widths))
    return "\n".join(lines)


def render_markdown(results: Sequence[LandscapeSanityResult]) -> str:
    """Render results as a markdown table."""

    if not results:
        return "No Events, Projects, or Ways found on this board."

    lines = [
        "| Piece | With WR | Without WR | Delta WR | With Avg | Without Avg | Delta Avg | Status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        lines.append(
            "| "
            + " | ".join(
                [
                    result.piece.label,
                    _format_pct(result.with_piece.win_rate),
                    _format_pct(result.without_piece.win_rate),
                    _format_pct(result.win_rate_delta, signed=True),
                    _format_num(result.with_piece.avg_score),
                    _format_num(result.without_piece.avg_score),
                    _format_num(result.avg_score_delta, signed=True),
                    result.status,
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect strategies whose results barely change when board landscapes are removed."
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="Strategy identifier accepted by StrategyLoader, e.g. VictoriaEngine.",
    )
    parser.add_argument(
        "--board",
        required=True,
        type=Path,
        help="Board definition file, e.g. boards/victoria_kingdom.txt.",
    )
    parser.add_argument(
        "--opponent",
        default=DEFAULT_OPPONENT,
        help=f"Opponent strategy identifier. Default: {DEFAULT_OPPONENT}.",
    )
    parser.add_argument("--games", type=int, default=100, help="Games per comparison run.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Win-rate delta threshold, in percentage points, below which a piece is flagged.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Base random seed.")
    parser.add_argument(
        "--format",
        choices=["table", "markdown"],
        default="table",
        help="Output format.",
    )
    parser.add_argument(
        "--use-shelters",
        action="store_true",
        help="Start games with Shelters instead of Estates.",
    )
    parser.add_argument(
        "--fail-on-ignore",
        action="store_true",
        help="Exit with status 1 when any landscape delta is below the threshold.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    board = load_board(args.board)
    results = analyze_landscapes(
        args.strategy,
        board,
        opponent_name=args.opponent,
        games=args.games,
        seed=args.seed,
        threshold=args.threshold,
        use_shelters=args.use_shelters,
    )

    renderer = render_markdown if args.format == "markdown" else render_table
    print(renderer(results))

    if args.fail_on_ignore and any(result.ignores_landscape for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
