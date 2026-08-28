"""Build linked static pages for all registered strategies and boards."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from typing import Iterable

from dominion.cards.allies._split_base import AlliesSplitCard
from dominion.cards.allies.wizards import WIZARDS_PILE_ORDER, WizardsSplitCard
from dominion.cards.dark_ages.knights import KNIGHT_NAMES
from dominion.cards.dark_ages.ruins import RUIN_VARIANT_NAMES
from dominion.cards.empires.castles import CASTLE_ORDER
from dominion.cards.registry import get_card
from dominion.cards.split_pile import SplitPileMixin
from dominion.reporting.board_pages import (
    RenderedBoard,
    collect_rendered_boards,
    render_board_index,
    render_board_page,
)
from dominion.reporting.strategy_links import PageLink
from dominion.reporting.strategy_pages import (
    RenderedStrategy,
    collect_rendered_strategies,
    existing_curated_strategy_guides,
    render_strategy_index,
    render_strategy_page,
)
from dominion.simulation.strategy_battle import canonical_landmark_name, canonical_way_name
from dominion.strategy.strategy_loader import StrategyLoader


def _relative_href(target: Path, source: Path) -> str:
    return Path(os.path.relpath(target, source.parent)).as_posix()


def _canonical_card_name(name: str) -> str:
    """Resolve a registered card alias while preserving unknown references."""

    try:
        return get_card(name).name
    except ValueError:
        return name


def _available_board_cards(board: RenderedBoard) -> set[str]:
    """Expand literal board entries with deterministic setup-created cards."""

    available = set(board.config.kingdom_cards)
    pending = list(available)
    while pending:
        name = pending.pop()
        card = get_card(name)
        additions = {card.name, *card.get_additional_piles()}
        additions.update(card.get_additional_non_supply_piles())
        additions.update(getattr(card, "nocturne_piles", {}))
        additions.update(getattr(card, "nocturne_trash_piles", {}))
        if getattr(card, "uses_boons", False):
            additions.add("Will-o'-Wisp")

        if isinstance(card, SplitPileMixin):
            additions.add(card.partner_card_name)
        if isinstance(card, WizardsSplitCard):
            additions.update(WIZARDS_PILE_ORDER)
        if isinstance(card, AlliesSplitCard):
            additions.update(card.pile_order)

        new_names = additions - available
        available.update(new_names)
        pending.extend(new_names)

    if available.intersection(CASTLE_ORDER):
        available.update(CASTLE_ORDER)
    if "Ruins" in available:
        available.update(RUIN_VARIANT_NAMES)
    if "Knights" in available:
        available.update(KNIGHT_NAMES)
    if "Black Market" in available or any(
        get_card(name).cost.potions for name in board.config.kingdom_cards
    ):
        available.add("Potion")

    return available


def strategy_is_compatible(strategy: RenderedStrategy, board: RenderedBoard) -> bool:
    """Return whether all of a strategy's board references exist on a board."""

    available = {
        "Kingdom Cards": _available_board_cards(board),
        "Events": set(board.config.events),
        "Projects": set(board.config.projects),
        "Ways": {canonical_way_name(name) for name in board.config.ways},
        "Landmarks": {
            canonical_landmark_name(name) for name in board.config.landmarks
        },
        "Allies": set(board.config.allies),
    }
    references = {
        **strategy.references,
        "Kingdom Cards": [
            _canonical_card_name(name) for name in strategy.references["Kingdom Cards"]
        ],
        "Ways": [canonical_way_name(name) for name in strategy.references["Ways"]],
        "Landmarks": [
            canonical_landmark_name(name) for name in strategy.references["Landmarks"]
        ],
    }
    return all(set(references[label]).issubset(values) for label, values in available.items())


def _link_catalog(
    strategies: list[RenderedStrategy],
    boards: list[RenderedBoard],
) -> tuple[list[RenderedStrategy], list[RenderedBoard]]:
    linked_strategies = []
    for strategy in strategies:
        source = Path("strategies") / f"{strategy.slug}.html"
        links = tuple(
            PageLink(
                board.display_name,
                _relative_href(Path("boards") / board.page_path, source),
            )
            for board in boards
            if strategy_is_compatible(strategy, board)
        )
        linked_strategies.append(replace(strategy, compatible_boards=links))

    linked_boards = []
    for board in boards:
        source = Path("boards") / board.page_path
        links = tuple(
            PageLink(
                strategy.display_name,
                _relative_href(Path("strategies") / f"{strategy.slug}.html", source),
            )
            for strategy in strategies
            if strategy_is_compatible(strategy, board)
        )
        linked_boards.append(replace(board, compatible_strategies=links))

    return linked_strategies, linked_boards


def render_catalog_pages(
    output_dir: Path = Path("reports"),
    *,
    boards_root: Path = Path("boards"),
    board_paths: Iterable[Path] | None = None,
    strategy_names: Iterable[str] | None = None,
    loader: StrategyLoader | None = None,
) -> list[Path]:
    """Write reciprocal board and strategy pages and return created paths."""

    strategies = collect_rendered_strategies(loader, names=strategy_names)
    boards = collect_rendered_boards(boards_root, paths=board_paths)
    strategies, boards = _link_catalog(strategies, boards)
    written: list[Path] = []

    strategy_dir = output_dir / "strategies"
    board_dir = output_dir / "boards"
    strategy_dir.mkdir(parents=True, exist_ok=True)
    board_dir.mkdir(parents=True, exist_ok=True)

    strategy_index = strategy_dir / "index.html"
    strategy_index.write_text(
        render_strategy_index(
            strategies,
            curated_guides=existing_curated_strategy_guides(strategy_dir),
            board_index_href="../boards/index.html",
        ),
        encoding="utf-8",
    )
    written.append(strategy_index)
    for strategy in strategies:
        path = strategy_dir / f"{strategy.slug}.html"
        path.write_text(render_strategy_page(strategy), encoding="utf-8")
        written.append(path)

    board_index = board_dir / "index.html"
    board_index.write_text(
        render_board_index(boards, strategy_index_href="../strategies/index.html"),
        encoding="utf-8",
    )
    written.append(board_index)
    for board in boards:
        path = board_dir / board.page_path
        path.parent.mkdir(parents=True, exist_ok=True)
        index_href = _relative_href(board_index.relative_to(output_dir), path.relative_to(output_dir))
        path.write_text(render_board_page(board, index_href=index_href), encoding="utf-8")
        written.append(path)

    return written
