"""Render Dominion board definitions as static HTML pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Iterable

from dominion.boards.loader import BoardConfig, load_board
from dominion.reporting.strategy_links import (
    PageLink,
    board_display_name,
    board_page_path,
)
from dominion.reporting.strategy_pages import (
    _card_chip,
    _landscape_chip,
    _page_shell,
    _typed_value_list,
)


@dataclass(frozen=True)
class RenderedBoard:
    display_name: str
    page_path: Path
    source_path: Path
    config: BoardConfig
    compatible_strategies: tuple[PageLink, ...] = field(default_factory=tuple)


def collect_rendered_boards(
    boards_root: Path = Path("boards"),
    *,
    paths: Iterable[Path] | None = None,
) -> list[RenderedBoard]:
    """Load board definitions and collect their page metadata."""

    board_paths = (
        list(paths) if paths is not None else sorted(boards_root.rglob("*.txt"))
    )
    return [
        RenderedBoard(
            display_name=board_display_name(path),
            page_path=board_page_path(path, boards_root=boards_root),
            source_path=path,
            config=load_board(path),
        )
        for path in board_paths
    ]


def _value_list(values: Iterable[str], kind: str = "Kingdom Cards") -> str:
    return _typed_value_list(values, kind)


def _link_list(links: Iterable[PageLink]) -> str:
    items = list(links)
    if not items:
        return '<span class="empty">None</span>'
    return (
        '<span class="chip-list">'
        + "".join(
            f'<a class="strategy-link-chip" href="{escape(link.href)}">{escape(link.label)}</a>'
            for link in items
        )
        + "</span>"
    )


def render_board_page(item: RenderedBoard, *, index_href: str) -> str:
    """Render a board definition and its compatible strategies."""

    config = item.config
    traits = [f"{trait} ({card})" for card, trait in sorted(config.traits.items())]
    body = f"""
<nav><a href="{escape(index_href)}">Board index</a></nav>
<header class="hero">
  <p class="eyebrow">Dominion board</p>
  <h1>{escape(item.display_name)}</h1>
  <p class="hero-description">A {len(config.kingdom_cards)}-card Kingdom with {len(item.compatible_strategies)} compatible registered {"strategy" if len(item.compatible_strategies) == 1 else "strategies"}.</p>
  <div class="hero-links"><strong>Compatible strategies</strong>{_link_list(item.compatible_strategies)}</div>
  <details class="technical-details">
    <summary>Setup details</summary>
    <dl class="meta">
      <dt>Source</dt><dd>{escape(str(item.source_path))}</dd>
      <dt>Events</dt><dd>{_value_list(config.events, "Events")}</dd>
      <dt>Projects</dt><dd>{_value_list(config.projects, "Projects")}</dd>
      <dt>Ways</dt><dd>{_value_list(config.ways, "Ways")}</dd>
      <dt>Landmarks</dt><dd>{_value_list(config.landmarks, "Landmarks")}</dd>
      <dt>Allies</dt><dd>{_value_list(config.allies, "Allies")}</dd>
      <dt>Traits</dt><dd>{_value_list(traits, "Traits")}</dd>
      <dt>Prophecy</dt><dd>{_landscape_chip(config.prophecy, "Prophecies") if config.prophecy else '<span class="empty">None</span>'}</dd>
      <dt>Card cost reduction</dt><dd><span class="coin-badge" aria-label="Coin cost reduction">{config.card_cost_reduction}</span></dd>
    </dl>
  </details>
</header>

<section class="section section-action">
  <div class="section-heading"><span class="section-icon" aria-hidden="true">K</span><h2>Kingdom Cards</h2></div>
  <div class="chip-list">{"".join(_card_chip(card) for card in config.kingdom_cards)}</div>
</section>
"""
    return _page_shell(f"{item.display_name} Board", body)


def render_board_index(items: list[RenderedBoard], *, strategy_index_href: str) -> str:
    rows = []
    for item in items:
        rows.append(
            '<article class="board-card board-row">'
            f'<h2><a href="{escape(item.page_path.as_posix())}">{escape(item.display_name)}</a></h2>'
            f'<div class="chip-list">{"".join(_card_chip(card) for card in item.config.kingdom_cards)}</div>'
            '<div class="card-footer">'
            f"<span>{len(item.config.kingdom_cards)} Kingdom cards</span>"
            f"<span>{len(item.compatible_strategies)} compatible {'strategy' if len(item.compatible_strategies) == 1 else 'strategies'}</span>"
            "</div>"
            "</article>"
        )

    body = f"""
<nav><a href="{escape(strategy_index_href)}">Strategy index</a></nav>
<header class="hero">
  <p class="eyebrow">Dominion simulator</p>
  <h1>Board Index</h1>
  <p class="hero-description">Browse configured Kingdoms, their cards, and compatible strategies.</p>
</header>
<label for="board-search" class="eyebrow">Find a board</label><br>
<input class="search" id="board-search" type="search" placeholder="Search by board or card name">
<div class="catalog-grid" id="board-grid">{"".join(rows)}</div>
<p class="empty-state" id="board-empty" hidden>No boards match that search.</p>
<script>
const search = document.getElementById('board-search');
const rows = Array.from(document.querySelectorAll('.board-row'));
const empty = document.getElementById('board-empty');
search.addEventListener('input', () => {{
  const query = search.value.toLowerCase();
  let visible = 0;
  for (const row of rows) {{
    const match = row.innerText.toLowerCase().includes(query);
    row.hidden = !match;
    if (match) visible += 1;
  }}
  empty.hidden = visible !== 0;
}});
</script>
"""
    return _page_shell("Board Index", body)
