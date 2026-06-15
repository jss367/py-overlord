"""Round-robin tournament between island champions.

Reads an island-evolution manifest (or a user-supplied list of strategy
names / champion file paths), then runs ``--games`` games for every pair
of strategies with alternating first player. Output is a Markdown win-rate
matrix and average-margin matrix written to stdout and optionally to a
file.

This is the deferred fair-comparison step: each island has had equal
optimization budget against the shared panel, so head-to-head results
between champions actually mean something.

Usage
-----
    # From a manifest (typical):
    python scripts/island_tournament.py --manifest generated_strategies/island_champions/<RUN_ID>/manifest.json --games 400

    # Ad-hoc strategy list (names or *.py paths):
    python scripts/island_tournament.py --strategies "Big Money" "Lisbon City Engine" generated_strategies/island_champions/.../lisbon_investment_rush_champion.py --games 200
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import logging
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import coloredlogs

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategy_loader import StrategyLoader


logger = logging.getLogger(__name__)


def _load_strategy_from_path(path: Path) -> tuple[str, EnhancedStrategy]:
    """Load a champion Python file produced by ``save_strategy_as_python``.

    Returns ``(display_name, strategy_instance)``. The display name comes
    from the strategy's ``name`` attribute, fall back to the file stem.
    """
    spec = importlib.util.spec_from_file_location(f"champion_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the EnhancedStrategy subclass defined in the module.
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ != module.__name__:
            continue
        if issubclass(obj, EnhancedStrategy) and obj is not EnhancedStrategy:
            instance = obj()
            name = getattr(instance, "name", path.stem)
            return name, instance

    raise RuntimeError(f"No EnhancedStrategy subclass found in {path}")


def _resolve_strategy(ref: str, loader: StrategyLoader) -> tuple[str, EnhancedStrategy]:
    """Resolve a strategy reference: file path or registered name."""
    p = Path(ref)
    if p.suffix == ".py" and p.exists():
        return _load_strategy_from_path(p)
    s = loader.get_strategy(ref)
    if s is None:
        raise ValueError(f"Unknown strategy: {ref!r}")
    return s.name, s


def _seed_refs_from_manifest(manifest: dict) -> tuple[list[str], int]:
    """Collect tournament-resolvable seed refs from a manifest's islands.

    Returns ``(refs, skipped)`` where ``refs`` are resolvable seed references
    (StrategyLoader names or ``*.py`` paths) and ``skipped`` counts islands with
    no resolvable seed (trick/random, or library seeds that don't round-trip).

    Board-derived manifests store ``seed_name`` as a DISPLAY name (``Reuse ...``,
    a trick name, ``Random Island 1``), which ``_resolve_strategy`` cannot
    resolve. Such manifests carry a separate ``seed_ref`` field (``None`` when
    there is no resolvable seed). For backward compatibility, manifests written
    before ``seed_ref`` existed (no island has the key) fall back to the old
    ``seed_name`` behavior so they don't hard-break.
    """
    islands = manifest.get("islands", [])
    has_seed_ref = any("seed_ref" in island for island in islands)
    if not has_seed_ref:
        # Legacy manifest: preserve prior behavior (resolve seed_name directly).
        return [island["seed_name"] for island in islands], 0

    refs: list[str] = []
    skipped = 0
    for island in islands:
        ref = island.get("seed_ref")
        if ref:
            refs.append(ref)
        else:
            skipped += 1
    return refs, skipped


def assemble_entrants(
    refs: list[str], loader: StrategyLoader
) -> list[tuple[str, str]]:
    """Resolve tournament entrant ``refs`` to ``(display_name, ref)`` pairs.

    Champions, ``--include-seeds`` seed refs, and ``--include-panel`` panel
    names are concatenated by the caller, and these lists legitimately overlap:
    on a board-derived manifest the seed refs and the panel both contain, e.g.,
    ``Big Money`` and the board's compatible library strategies. Appending them
    unconditionally would feed the same entrant in twice.

    Dedup is by *ref identity*: when the exact same ref string appears more than
    once (the intended overlap between champions/seeds/panel), only the first
    occurrence is kept, preserving order. A genuine collision — two *distinct*
    refs that resolve to the same display name (which would silently overwrite
    matrix cells keyed on the name) — is still rejected with ``ValueError``, so
    the guard against accidental name clashes is preserved.
    """
    resolved: list[tuple[str, str]] = []
    seen_refs: set[str] = set()
    name_to_ref: dict[str, str] = {}
    for ref in refs:
        if ref in seen_refs:
            continue
        name, _ = _resolve_strategy(ref, loader)
        prior_ref = name_to_ref.get(name)
        if prior_ref is not None:
            # Distinct refs resolving to the same display name: a real clash.
            raise ValueError(
                f"Duplicate display name {name!r} from distinct entrants "
                f"{prior_ref!r} and {ref!r}. Rename or deduplicate before running."
            )
        seen_refs.add(ref)
        name_to_ref[name] = ref
        resolved.append((name, ref))
    return resolved


DEFAULT_BOARD = "boards/lisbon.txt"


def resolve_tournament_board(
    cli_board: Optional[str], manifest: Optional[dict]
) -> tuple[str, str]:
    """Resolve which board the tournament should run on.

    Precedence: explicit ``--board`` > the manifest's training board (only when
    a manifest is supplied) > the ``boards/lisbon.txt`` fallback. Returns
    ``(board_path, source)`` where ``source`` is one of ``"CLI"``,
    ``"manifest"``, or ``"default"`` (used purely for an informative log line).
    """
    if cli_board:
        return cli_board, "CLI"
    if manifest:
        board = manifest.get("board")
        if board:
            return board, "manifest"
    return DEFAULT_BOARD, "default"


def _matchup_unique_key(a: str, b: str) -> tuple[str, str]:
    """Order-independent key for a matchup (so we don't run A-vs-B twice)."""
    return (a, b) if a <= b else (b, a)


@dataclass
class Matchup:
    a: str
    b: str
    games: int


def _run_matchup(
    a_ref: str,
    b_ref: str,
    games: int,
    board_path: str,
) -> dict:
    """Play ``games`` games between strategies ``a_ref`` and ``b_ref`` on the
    given board. Returns a result dict with wins, margins, and turn counts.

    Lives at module level so it can be sent to a ProcessPoolExecutor."""
    loader = StrategyLoader()
    a_name, a_strategy = _resolve_strategy(a_ref, loader)
    b_name, b_strategy = _resolve_strategy(b_ref, loader)

    board_config = load_board(board_path)
    battle = StrategyBattle(
        kingdom_cards=board_config.kingdom_cards,
        board_config=board_config,
        log_frequency=0,
    )

    a_wins = 0
    a_total_score = 0
    b_total_score = 0
    total_turns = 0

    for i in range(games):
        ai_a = GeneticAI(a_strategy)
        ai_b = GeneticAI(b_strategy)
        # Alternate first player to remove the seat advantage.
        if i % 2 == 0:
            winner, scores, _, turns = battle.run_game(
                ai_a, ai_b, board_config.kingdom_cards
            )
        else:
            winner, scores, _, turns = battle.run_game(
                ai_b, ai_a, board_config.kingdom_cards
            )
        if winner == ai_a:
            a_wins += 1
        a_total_score += scores.get(ai_a.name, 0)
        b_total_score += scores.get(ai_b.name, 0)
        total_turns += turns

    return {
        "a_name": a_name,
        "b_name": b_name,
        "games": games,
        "a_wins": a_wins,
        "b_wins": games - a_wins,
        "a_win_rate": a_wins / games * 100,
        "avg_a_score": a_total_score / games,
        "avg_b_score": b_total_score / games,
        "avg_margin": (a_total_score - b_total_score) / games,
        "avg_turns": total_turns / games,
    }


def _format_matrix(names: list[str], cell: dict[tuple[str, str], str]) -> str:
    """Format a row=A, col=B matrix where each cell is filled by ``cell[(a, b)]``."""
    header = "| | " + " | ".join(names) + " |"
    sep = "|---|" + "|".join(["---"] * len(names)) + "|"
    rows = [header, sep]
    for a in names:
        row = [a]
        for b in names:
            if a == b:
                row.append("—")
            else:
                row.append(cell.get((a, b), "?"))
        rows.append("| " + " | ".join(row) + " |")
    return "\n".join(rows)


def main() -> None:
    coloredlogs.install(level="INFO", logger=logging.getLogger())

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", help="Path to an island_evolve manifest.json.")
    parser.add_argument(
        "--strategies",
        nargs="+",
        help="Explicit strategy refs (names or *.py paths). Used if --manifest is omitted.",
    )
    parser.add_argument(
        "--include-seeds",
        action="store_true",
        help=(
            "When using --manifest, also include the original seed names in the "
            "tournament so champions can be compared against their starting points."
        ),
    )
    parser.add_argument(
        "--include-panel",
        action="store_true",
        help="When using --manifest, also include each panel member as a tournament entrant.",
    )
    parser.add_argument(
        "--board",
        default=None,
        help=(
            "Board to evaluate on. Defaults to the manifest's training board "
            "(when --manifest is used) and otherwise to boards/lisbon.txt. An "
            "explicit value always wins."
        ),
    )

    def _positive_int(value: str) -> int:
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
        return ivalue

    # Validated at parse time: ``_run_matchup`` divides by ``games`` to
    # compute win rates and averages, so 0/negative would crash or produce
    # nonsense.
    parser.add_argument("--games", type=_positive_int, default=400)
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run matchups in parallel using multiprocessing.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=0,
        help="Cap parallel workers. 0 = number of matchups.",
    )
    parser.add_argument("--output", help="Write the Markdown report to this path.")
    args = parser.parse_args()

    refs: list[str] = []
    manifest: Optional[dict] = None
    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest = json.loads(manifest_path.read_text())
        # Use file paths so we load the actual evolved champions, not the
        # original named seeds.
        for island in manifest.get("islands", []):
            refs.append(island["output_path"])
        if args.include_seeds:
            seed_refs, skipped = _seed_refs_from_manifest(manifest)
            refs.extend(seed_refs)
            if skipped:
                logger.info(
                    "Skipping %d island(s) with no resolvable seed (trick/random)",
                    skipped,
                )
        if args.include_panel:
            refs.extend(manifest.get("panel", []))
    elif args.strategies:
        refs = list(args.strategies)
    else:
        parser.error("Provide either --manifest or --strategies")

    board_path, board_source = resolve_tournament_board(args.board, manifest)
    logger.info("Tournament board: %s (from %s)", board_path, board_source)

    # Resolve once up-front so misspelled names fail immediately. The helper
    # dedupes the intended overlap between champions/seeds/panel (same ref
    # appearing twice) and still rejects distinct refs that collide by display
    # name — duplicate names would silently overwrite the matrix cells keyed on
    # (a_name, b_name) and corrupt the report.
    loader = StrategyLoader()
    try:
        resolved = assemble_entrants(refs, loader)  # (display_name, ref-for-subprocess)
    except ValueError as exc:
        parser.error(str(exc))

    # Ordered list of entrant display names — drives the matrix rows/columns
    # and the average-win-rate ranking below.
    names = [name for name, _ in resolved]

    # Build matchup list (one entry per unordered pair).
    matchups: list[tuple[str, str, str, str]] = []  # (a_name, b_name, a_ref, b_ref)
    for i, (a_name, a_ref) in enumerate(resolved):
        for j, (b_name, b_ref) in enumerate(resolved):
            if j <= i:
                continue
            matchups.append((a_name, b_name, a_ref, b_ref))

    logger.info(
        "Tournament: %d strategies, %d matchups, %d games each",
        len(resolved),
        len(matchups),
        args.games,
    )

    raw_results: list[dict] = []
    # A failed matchup means the absent cells get rendered as "?" and the
    # average-win-rate column is computed from fewer opponents than the
    # rest, silently biasing the ranking. Track failures and refuse to
    # publish a partial report.
    failed_matchups: list[tuple[str, str]] = []
    if args.parallel and len(matchups) > 1:
        max_workers = args.max_workers or len(matchups)
        ctx = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as ex:
            futures = {
                ex.submit(_run_matchup, a_ref, b_ref, args.games, board_path): (a_name, b_name)
                for a_name, b_name, a_ref, b_ref in matchups
            }
            for fut in as_completed(futures):
                pair = futures[fut]
                try:
                    r = fut.result()
                    raw_results.append(r)
                    logger.info(
                        "%s vs %s: %.1f%% (margin %+.1f)",
                        r["a_name"], r["b_name"], r["a_win_rate"], r["avg_margin"],
                    )
                except Exception:
                    logger.exception("Matchup %s failed", pair)
                    failed_matchups.append(pair)
    else:
        for a_name, b_name, a_ref, b_ref in matchups:
            try:
                r = _run_matchup(a_ref, b_ref, args.games, board_path)
                raw_results.append(r)
                logger.info(
                    "%s vs %s: %.1f%% (margin %+.1f)",
                    r["a_name"], r["b_name"], r["a_win_rate"], r["avg_margin"],
                )
            except Exception:
                logger.exception("Matchup (%s, %s) failed", a_name, b_name)
                failed_matchups.append((a_name, b_name))

    if failed_matchups:
        logger.error(
            "Tournament incomplete — %d/%d matchups failed: %s. Not publishing report.",
            len(failed_matchups), len(matchups), failed_matchups,
        )
        sys.exit(1)

    # Build cell maps. Each result for (a, b) gives us:
    #   - a_win_rate for cell (a, b)
    #   - (100 - a_win_rate) for cell (b, a)
    win_cell: dict[tuple[str, str], str] = {}
    margin_cell: dict[tuple[str, str], str] = {}
    for r in raw_results:
        a, b = r["a_name"], r["b_name"]
        win_cell[(a, b)] = f"{r['a_win_rate']:.1f}%"
        win_cell[(b, a)] = f"{100 - r['a_win_rate']:.1f}%"
        margin_cell[(a, b)] = f"{r['avg_margin']:+.1f}"
        margin_cell[(b, a)] = f"{-r['avg_margin']:+.1f}"

    # Add an "average win rate" column. For each strategy, average its win
    # rate across all opponents — the single number that ranks champions.
    avg_win: dict[str, float] = {}
    for name in names:
        rates = []
        for other in names:
            if other == name:
                continue
            cell = win_cell.get((name, other))
            if cell:
                rates.append(float(cell.rstrip("%")))
        avg_win[name] = sum(rates) / max(1, len(rates))

    lines = []
    board_label = Path(board_path).stem.replace("_", " ").title()
    lines.append(f"# {board_label} Island Tournament — {args.games} games / matchup\n")
    lines.append(f"Board: `{board_path}`\n")
    lines.append("## Win-rate matrix (row vs column)\n")
    lines.append(_format_matrix(names, win_cell))
    lines.append("\n## Average VP margin matrix (row minus column)\n")
    lines.append(_format_matrix(names, margin_cell))
    lines.append("\n## Average win rate (ranked)\n")
    lines.append("| Strategy | Avg win % |")
    lines.append("|---|---|")
    for name, rate in sorted(avg_win.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {name} | {rate:.1f}% |")
    report = "\n".join(lines) + "\n"

    print(report)
    if args.output:
        Path(args.output).write_text(report)
        logger.info("Wrote report to %s", args.output)


if __name__ == "__main__":
    main()
