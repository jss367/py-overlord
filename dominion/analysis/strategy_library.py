"""Discover and rank reusable strategy seeds for a target board.

The genetic trainer can already inject hand-picked seed strategies. This module
adds a lightweight retrieval layer: inspect existing strategy modules, extract
the non-base cards their rules reference, and rank them by overlap with a new
board. A compatible old strategy is only a hypothesis; training still has to
mutate it and prove it against the fitness panel.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from dominion.strategy.enhanced_strategy import EnhancedStrategy

logger = logging.getLogger(__name__)


BASE_SUPPLY_CARDS = frozenset(
    {
        "Copper",
        "Silver",
        "Gold",
        "Platinum",
        "Estate",
        "Duchy",
        "Province",
        "Colony",
        "Curse",
    }
)

RULE_LIST_ATTRS = (
    "gain_priority",
    "action_priority",
    "treasure_priority",
    "trash_priority",
    "discard_priority",
)


@dataclass(frozen=True)
class StrategyLibraryEntry:
    """A strategy candidate ranked for reuse on a specific target board."""

    name: str
    spec: str
    factory: Callable[[], EnhancedStrategy]
    referenced_cards: frozenset[str]
    core_cards: frozenset[str]
    matched_cards: frozenset[str]
    missing_cards: frozenset[str]
    score: float


def referenced_cards(strategy: EnhancedStrategy) -> frozenset[str]:
    """Return card names directly referenced by a strategy's priority rules."""

    names: set[str] = set()
    for attr in RULE_LIST_ATTRS:
        for rule in getattr(strategy, attr, []) or []:
            card = getattr(rule, "card_name", None) or getattr(rule, "card", None)
            if card:
                names.add(card)

    for rule in getattr(strategy, "way_policy", []) or []:
        card = getattr(rule, "card_name", None)
        if card:
            names.add(card)

    return frozenset(names)


def score_strategy_for_board(
    strategy: EnhancedStrategy,
    board_cards: Iterable[str],
) -> tuple[float, frozenset[str], frozenset[str], frozenset[str]]:
    """Score a strategy against a target board.

    Base supply cards are ignored. The score intentionally rewards concrete
    overlap more than pure coverage: a 4-card known engine with one missing
    card should usually rank above a 1-card strategy with perfect coverage.
    """

    board_set = set(board_cards)
    refs = referenced_cards(strategy)
    core = frozenset(refs - BASE_SUPPLY_CARDS)
    if not core:
        return 0.0, core, frozenset(), frozenset()

    matched = frozenset(core & board_set)
    missing = frozenset(core - board_set)
    coverage = len(matched) / len(core)
    score = (len(matched) * 10.0) + (coverage * 10.0) - (len(missing) * 2.0)
    return score, core, matched, missing


def default_strategy_locations(root: Path | None = None) -> list[tuple[Path, str]]:
    """Return the built-in strategy locations and import prefixes."""

    if root is None:
        root = Path.cwd()
    return [
        (root / "generated_strategies", "generated_strategies"),
        (
            root / "dominion" / "strategy" / "strategies",
            "dominion.strategy.strategies",
        ),
    ]


def _iter_strategy_factories(
    locations: Sequence[tuple[Path, str]],
) -> Iterable[tuple[str, Callable[[], EnhancedStrategy]]]:
    for directory, module_prefix in locations:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.py")):
            if path.stem == "__init__":
                continue
            module_name = f"{module_prefix}.{path.stem}"
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:
                logger.debug("Skipping strategy module %s: %s", module_name, exc)
                continue
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith("create_"):
                    continue
                spec = f"{module_name}:{name}"
                yield spec, obj


def find_compatible_strategies(
    board_cards: Iterable[str],
    *,
    top_k: int = 5,
    min_overlap: int = 2,
    locations: Sequence[tuple[Path, str]] | None = None,
) -> list[StrategyLibraryEntry]:
    """Find existing strategies that reference cards on ``board_cards``.

    ``min_overlap`` is the minimum number of non-base cards a strategy must
    share with the target board. Returned entries are ordered from strongest
    to weakest match.
    """

    if locations is None:
        locations = default_strategy_locations()

    entries: list[StrategyLibraryEntry] = []
    seen_specs: set[str] = set()
    for spec, factory in _iter_strategy_factories(locations):
        if spec in seen_specs:
            continue
        seen_specs.add(spec)
        try:
            strategy = factory()
        except Exception as exc:
            logger.debug("Skipping strategy factory %s: %s", spec, exc)
            continue

        score, core, matched, missing = score_strategy_for_board(strategy, board_cards)
        if len(matched) < min_overlap:
            continue

        entries.append(
            StrategyLibraryEntry(
                name=getattr(strategy, "name", "") or spec.rsplit(":", 1)[1],
                spec=spec,
                factory=factory,
                referenced_cards=referenced_cards(strategy),
                core_cards=core,
                matched_cards=matched,
                missing_cards=missing,
                score=score,
            )
        )

    entries.sort(
        key=lambda e: (
            e.score,
            len(e.matched_cards),
            -len(e.missing_cards),
            e.name,
        ),
        reverse=True,
    )
    return entries[: max(0, top_k)]
