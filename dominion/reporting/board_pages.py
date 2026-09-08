"""Render Dominion board definitions as static HTML pages."""

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Iterable

from dominion.boards.loader import BoardConfig, load_board
from dominion.cards.registry import get_card
from dominion.reporting.strategy_links import (
    PageLink,
    board_display_name,
    board_page_path,
)
from dominion.reporting.strategy_pages import (
    _PRIMARY_CARD_TYPES,
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


# Basic piles can be explicitly included in a board file, but are not Kingdom piles.
_BASIC_PILES = {"Copper", "Silver", "Gold", "Platinum", "Estate", "Duchy", "Province", "Colony", "Curse", "Potion"}

_BOARD_STYLES = """
    .card-chip, .landscape-chip, .strategy-link-chip { white-space: normal; max-width: 100%; overflow-wrap: anywhere; }
    .card-chip > span { min-width: 0; }
    .board-hero { background: #183f42; color: #fffdf8; }
    .board-hero .eyebrow { color: #c8dcae; }
    .board-hero .hero-description { color: #dde6df; }
    .board-stats { display: flex; flex-wrap: wrap; gap: 12px 28px; margin-top: 26px; }
    .board-stats span { color: #dde6df; font-size: .85rem; }
    .board-stats strong { color: white; font-size: 1.35rem; margin-right: 5px; }
    .kingdom-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
    .pile-card { background: var(--surface); border: 1px solid var(--border); border-top: 5px solid var(--pile-color, #b7aa91); border-radius: 12px; box-shadow: 0 5px 16px rgb(64 48 28 / 5%); padding: 18px 14px; min-width: 0; display: flex; flex-direction: column; gap: 14px; }
    .pile-action { --pile-color: #b7aa91; }
    .pile-treasure { --pile-color: #c59c3b; }
    .pile-victory { --pile-color: #6f9959; }
    .pile-night { --pile-color: #635c79; }
    .pile-curse { --pile-color: #9270ac; }
    .pile-card h3 { font: 700 1.12rem Georgia, serif; line-height: 1.3; margin: 0; overflow-wrap: anywhere; }
    .pile-card h3 .card-chip { background: transparent; color: inherit; border: 0; border-radius: 0; box-shadow: none; padding: 0; font: inherit; min-height: 0; }
    .pile-card .type-marker { display: none; }
    .pile-types { color: #625a50; font-size: .75rem; margin: 0; }
    .pile-cost { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-top: auto; font-size: .75rem; }
    .pile-cost .coin-badge { flex-shrink: 0; }
    .cost-extra { background: #eee8df; border-radius: 5px; padding: 3px 6px; }
    .landscape-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr)); gap: 12px; }
    .landscape-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
    .landscape-panel h3 { margin: 0 0 12px; font-size: .78rem; color: var(--muted); letter-spacing: .06em; text-transform: uppercase; }
    .setup-note { border-left: 4px solid #bb943f; background: #fff6dc; padding: 14px 18px; border-radius: 4px 10px 10px 4px; margin: 18px 0; }
    .board-source { margin-top: 30px; color: var(--muted); font-size: .85rem; overflow-wrap: anywhere; }
    .board-source summary { cursor: pointer; }
    .board-toolbar { margin: 24px 0; }
    .board-toolbar label { display: block; }
    .board-toolbar .search { margin: 8px 0; }
    .board-results { margin: 0; color: var(--muted); font-size: .85rem; }
    .board-card .board-preview-landscapes { border-top: 1px solid var(--border); padding-top: 12px; }
    .board-preview-landscapes .landscape-chip { font-size: .72rem; }
    .board-footer { margin-top: 40px; border-top: 1px solid var(--border); padding-top: 18px; color: var(--muted); font-size: .8rem; }
    a:focus-visible, summary:focus-visible { outline: 3px solid #a77f21; outline-offset: 4px; }
    @media (max-width: 1000px) { .kingdom-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
    @media (max-width: 600px) { .kingdom-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; } .pile-card { padding: 14px 12px; } }
    @media (prefers-reduced-motion: reduce) { .board-card { transition: none; } .board-card:hover { transform: none; } }
    @media print {
      .board-hero { background: white; color: black; }
      .board-hero .eyebrow, .board-hero .hero-description, .board-stats span, .board-stats strong { color: black; }
      .kingdom-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); }
      .pile-card, .landscape-panel { break-inside: avoid; box-shadow: none; }
      .board-toolbar { display: none; }
    }
"""


def _kingdom_cards(config: BoardConfig) -> list[str]:
    return [name for name in config.kingdom_cards if name not in _BASIC_PILES]


def _landscapes(config: BoardConfig) -> list[tuple[str, list[str]]]:
    groups = [
        ("Events", config.events),
        ("Projects", config.projects),
        ("Ways", config.ways),
        ("Landmarks", config.landmarks),
        ("Allies", config.allies),
        ("Traits", [f"{trait} ({card})" for card, trait in sorted(config.traits.items())]),
        ("Prophecies", [config.prophecy] if config.prophecy else []),
    ]
    return [(kind, values) for kind, values in groups if values]


def _pile_card(name: str, *, trait: str | None = None) -> str:
    try:
        card = get_card(name)
    except (KeyError, ValueError):
        types, cost, primary = "Card details unavailable", "", "other"
    else:
        primary = next((kind.value for kind in _PRIMARY_CARD_TYPES if kind in card.types), "other")
        types = " · ".join(kind.value.title() for kind in card.types)
        cost = f'<span class="coin-badge" aria-label="{card.cost.coins} coins">{card.cost.coins}</span>'
        if card.cost.potions:
            cost += f'<span class="cost-extra">{card.cost.potions} potion{ "s" if card.cost.potions != 1 else ""}</span>'
        if card.cost.debt:
            cost += f'<span class="cost-extra">{card.cost.debt} debt</span>'
    trait_html = _landscape_chip(trait, "Traits") if trait else ""
    return (
        f'<article class="pile-card pile-{primary}">'
        f'<h3>{_card_chip(name)}</h3><p class="pile-types">{escape(types)}</p>'
        f'{trait_html}<div class="pile-cost">{cost}</div></article>'
    )


def render_board_page(item: RenderedBoard, *, index_href: str) -> str:
    """Render a browser-ready board with visible cards, landscapes and strategies."""

    config = item.config
    kingdom = _kingdom_cards(config)
    basic = [name for name in config.kingdom_cards if name in _BASIC_PILES]
    landscapes = _landscapes(config)
    landscape_count = sum(len(values) for _, values in landscapes)
    landscape_html = "".join(
        f'<article class="landscape-panel"><h3>{kind}</h3>{_value_list(values, kind)}</article>'
        for kind, values in landscapes
    )
    basic_html = (
        '<section class="section" aria-labelledby="basic-heading"><div class="section-heading">'
        '<h2 id="basic-heading">Additional basic piles</h2></div>'
        '<p class="section-note">Basic piles explicitly included in this board’s setup.</p>'
        f'<div class="kingdom-grid">{"".join(_pile_card(name) for name in basic)}</div></section>'
        if basic else ""
    )
    discount_html = (
        f'<p class="setup-note"><strong>Card cost reduction: {config.card_cost_reduction} coin{ "s" if config.card_cost_reduction != 1 else ""}.</strong> '
        'Every card costs this much less, to a minimum of zero coins. Debt and potion costs are unchanged. Tiles show printed costs.</p>'
        if config.card_cost_reduction else ""
    )
    body = f"""
<nav aria-label="Catalog navigation"><a href="{escape(index_href)}">Board index</a></nav>
<main>
<header class="hero board-hero">
  <p class="eyebrow">Dominion · Kingdom setup</p>
  <h1>{escape(item.display_name)}</h1>
  <p class="hero-description">Your table at a glance. Explore the Kingdom, check the setup, and find a strategy to play.</p>
  <div class="board-stats">
    <span><strong>{len(kingdom)}</strong> Kingdom cards</span>
    <span><strong>{landscape_count}</strong> {"landscape" if landscape_count == 1 else "landscapes"}</span>
    <span><strong>{len(item.compatible_strategies)}</strong> compatible {"strategy" if len(item.compatible_strategies) == 1 else "strategies"}</span>
  </div>
</header>
{discount_html}
<section class="section" aria-labelledby="kingdom-heading">
  <div class="section-heading"><h2 id="kingdom-heading">Kingdom Cards</h2></div>
  <p class="section-note">Printed costs and card types. In-game effects may change costs.</p>
  <div class="kingdom-grid">{"".join(_pile_card(card, trait=config.traits.get(card)) for card in kingdom)}</div>
</section>
{basic_html}
<section class="section" aria-labelledby="landscapes-heading">
  <div class="section-heading"><h2 id="landscapes-heading">Landscapes &amp; setup</h2></div>
  {f'<div class="landscape-grid">{landscape_html}</div>' if landscapes else '<p class="empty-state">No landscapes specified for this board.</p>'}
</section>
<section class="section" aria-labelledby="strategies-heading">
  <div class="section-heading"><h2 id="strategies-heading">Compatible strategies</h2></div>
  <p class="section-note">These strategies reference cards and landscapes available on this board.</p>
  {_link_list(item.compatible_strategies) if item.compatible_strategies else '<p class="empty-state">No compatible strategies in the catalog yet.</p>'}
</section>
<details class="board-source"><summary>Setup details</summary><p>Source: <code>{escape(str(item.source_path))}</code></p></details>
</main>
<footer class="board-footer">Dominion board library · <a href="{escape(index_href)}">Browse all boards</a></footer>
"""
    return _page_shell(f"{item.display_name} Board", body, extra_styles=_BOARD_STYLES)


def render_board_index(items: list[RenderedBoard], *, strategy_index_href: str) -> str:
    rows = []
    for item in items:
        landscapes = "".join(
            _landscape_chip(value, kind)
            for kind, values in _landscapes(item.config)
            for value in values
        )
        landscape_preview = f'<div class="chip-list board-preview-landscapes">{landscapes}</div>' if landscapes else ""
        discount = (
            f'<p>Card cost reduction: {item.config.card_cost_reduction} {"coin" if item.config.card_cost_reduction == 1 else "coins"}</p>'
            if item.config.card_cost_reduction else ""
        )
        rows.append(
            '<article class="board-card board-row">'
            f'<h2><a href="{escape(item.page_path.as_posix())}">{escape(item.display_name)}</a></h2>'
            f'<div class="chip-list">{"".join(_card_chip(card) for card in item.config.kingdom_cards)}</div>'
            f'{landscape_preview}{discount}'
            '<div class="card-footer">'
            f"<span>{len(_kingdom_cards(item.config))} Kingdom cards</span>"
            f"<span>{len(item.compatible_strategies)} compatible {'strategy' if len(item.compatible_strategies) == 1 else 'strategies'}</span>"
            "</div></article>"
        )

    body = f"""
<nav aria-label="Catalog navigation"><a href="{escape(strategy_index_href)}">Strategy index</a></nav>
<main>
<header class="hero board-hero">
  <p class="eyebrow">Dominion · Board library</p>
  <h1>Find your next Kingdom.</h1>
  <p class="hero-description">Browse {len(items)} boards, explore their cards and landscapes, and discover compatible strategies.</p>
</header>
<div class="board-toolbar">
  <label for="board-search" class="eyebrow">Find a board</label>
  <input class="search" id="board-search" type="search" placeholder="Search boards, cards, or landscapes" aria-describedby="board-results">
  <p class="board-results" id="board-results" role="status" aria-live="polite">Showing {len(items)} of {len(items)} boards</p>
</div>
<div class="catalog-grid" id="board-grid">{"".join(rows)}</div>
<p class="empty-state" id="board-empty" hidden>No boards match that search. Try another card, landscape, or board name.</p>
</main>
<footer class="board-footer">Dominion board library · <a href="{escape(strategy_index_href)}">Explore the strategy catalog</a></footer>
<script>
const search = document.getElementById('board-search');
const rows = Array.from(document.querySelectorAll('.board-row'));
const entries = rows.map(row => ({{ row, text: row.textContent.toLowerCase() }}));
const empty = document.getElementById('board-empty');
const results = document.getElementById('board-results');
function filterBoards() {{
  const words = search.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);
  let visible = 0;
  for (const {{ row, text }} of entries) {{
    const match = words.every(word => text.includes(word));
    row.hidden = !match;
    if (match) visible += 1;
  }}
  results.textContent = `Showing ${{visible}} of ${{rows.length}} boards`;
  empty.hidden = visible !== 0;
}}
search.addEventListener('input', filterBoards);
filterBoards();
</script>
"""
    return _page_shell("Board Index", body, extra_styles=_BOARD_STYLES)
