"""Render Dominion board definitions as static HTML pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Iterable

from dominion.boards.loader import BoardConfig, load_board
from dominion.reporting.strategy_links import PageLink, board_display_name, board_page_path
from dominion.reporting.strategy_pages import _page_shell


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

    board_paths = list(paths) if paths is not None else sorted(boards_root.rglob("*.txt"))
    return [
        RenderedBoard(
            display_name=board_display_name(path),
            page_path=board_page_path(path, boards_root=boards_root),
            source_path=path,
            config=load_board(path),
        )
        for path in board_paths
    ]


def _value_list(values: Iterable[str]) -> str:
    items = list(values)
    if not items:
        return '<span class="empty">None</span>'
    return ", ".join(escape(item) for item in items)


def _link_list(links: Iterable[PageLink]) -> str:
    items = list(links)
    if not items:
        return '<span class="empty">None</span>'
    return ", ".join(
        f'<a href="{escape(link.href)}">{escape(link.label)}</a>' for link in items
    )


def render_board_page(item: RenderedBoard, *, index_href: str) -> str:
    """Render a board definition and its compatible strategies."""

    config = item.config
    traits = [f"{trait} ({card})" for card, trait in sorted(config.traits.items())]
    body = f"""
<nav><a href="{escape(index_href)}">Board index</a></nav>
<h1>{escape(item.display_name)}</h1>
<p class="muted">Source: {escape(str(item.source_path))}</p>

<h2>Kingdom Cards</h2>
<ol>{''.join(f'<li>{escape(card)}</li>' for card in config.kingdom_cards)}</ol>

<h2>Landscapes and Setup</h2>
<dl class="meta">
  <dt>Events</dt><dd>{_value_list(config.events)}</dd>
  <dt>Projects</dt><dd>{_value_list(config.projects)}</dd>
  <dt>Ways</dt><dd>{_value_list(config.ways)}</dd>
  <dt>Landmarks</dt><dd>{_value_list(config.landmarks)}</dd>
  <dt>Allies</dt><dd>{_value_list(config.allies)}</dd>
  <dt>Traits</dt><dd>{_value_list(traits)}</dd>
  <dt>Prophecy</dt><dd>{escape(config.prophecy) if config.prophecy else '<span class="empty">None</span>'}</dd>
  <dt>Card cost reduction</dt><dd>${config.card_cost_reduction}</dd>
</dl>

<h2>Compatible Strategies</h2>
<p>{_link_list(item.compatible_strategies)}</p>
"""
    return _page_shell(f"{item.display_name} Board", body)


def render_board_index(items: list[RenderedBoard], *, strategy_index_href: str) -> str:
    rows = []
    for item in items:
        rows.append(
            '<tr class="board-row">'
            f'<td><a href="{escape(item.page_path.as_posix())}">{escape(item.display_name)}</a></td>'
            f"<td>{_value_list(item.config.kingdom_cards)}</td>"
            f"<td>{len(item.compatible_strategies)}</td>"
            f"<td>{escape(str(item.source_path))}</td>"
            "</tr>"
        )

    body = f"""
<nav><a href="{escape(strategy_index_href)}">Strategy index</a></nav>
<h1>Board Index</h1>
<p class="muted">Generated from board definition files. Regenerate this catalog after changing a board.</p>
<input class="search" id="board-search" type="search" placeholder="Search boards">
<table id="board-table">
  <tr><th>Board</th><th>Kingdom Cards</th><th>Compatible Strategies</th><th>Source</th></tr>
  {''.join(rows)}
</table>
<script>
const search = document.getElementById('board-search');
const rows = Array.from(document.querySelectorAll('.board-row'));
search.addEventListener('input', () => {{
  const query = search.value.toLowerCase();
  for (const row of rows) {{
    row.style.display = row.innerText.toLowerCase().includes(query) ? '' : 'none';
  }}
}});
</script>
"""
    return _page_shell("Board Index", body)
