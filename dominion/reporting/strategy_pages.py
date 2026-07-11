"""Render registered strategies as static HTML pages."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import inspect
from pathlib import Path
from typing import Iterable

from dominion.simulation.strategy_battle import StrategyBattle
from dominion.reporting.strategy_links import strategy_page_href, strategy_slug
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule, WayRule
from dominion.strategy.strategy_loader import StrategyLoader


@dataclass(frozen=True)
class RenderedStrategy:
    display_name: str
    slug: str
    strategy: EnhancedStrategy
    source_path: str
    factory_name: str
    references: dict[str, list[str]]


def _condition_label(condition) -> str:
    if condition is None:
        return "always"
    return str(getattr(condition, "_source", "custom condition"))


def _priority_rows(rules: Iterable[PriorityRule]) -> str:
    rows = []
    for index, rule in enumerate(rules, 1):
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{escape(rule.card_name)}</td>"
            f"<td>{escape(_condition_label(rule.condition))}</td>"
            "</tr>"
        )
    if not rows:
        return "<tr><td colspan=\"3\" class=\"empty\">None</td></tr>"
    return "\n".join(rows)


def _way_rows(rules: Iterable[WayRule]) -> str:
    rows = []
    for index, rule in enumerate(rules, 1):
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{escape(rule.card_name)}</td>"
            f"<td>{escape(rule.way_name)}</td>"
            f"<td>{escape(_condition_label(rule.condition))}</td>"
            "</tr>"
        )
    if not rows:
        return "<tr><td colspan=\"4\" class=\"empty\">None</td></tr>"
    return "\n".join(rows)


def _reference_list(values: list[str]) -> str:
    if not values:
        return "<span class=\"empty\">None</span>"
    return ", ".join(escape(value) for value in values)


def _strategy_source(loader: StrategyLoader, display_name: str) -> tuple[str, str]:
    factory = loader.strategies.get(display_name)
    if factory is None:
        factory = loader.strategies.get(display_name.lower())
    if factory is None:
        return "", ""

    source = inspect.getsourcefile(factory) or ""
    try:
        source = str(Path(source).resolve().relative_to(Path.cwd()))
    except ValueError:
        source = str(Path(source).resolve()) if source else ""
    return source, getattr(factory, "__name__", "")


def collect_rendered_strategies(
    loader: StrategyLoader | None = None,
    *,
    names: Iterable[str] | None = None,
) -> list[RenderedStrategy]:
    """Instantiate registered strategies and collect metadata for rendering."""

    loader = loader or StrategyLoader()
    battle = StrategyBattle(log_frequency=0)
    display_names = list(names) if names is not None else loader.list_strategies()
    rendered = []

    for display_name in sorted(display_names):
        strategy = loader.get_strategy(display_name)
        if strategy is None:
            raise ValueError(f"Unknown strategy: {display_name}")

        refs = battle._split_board_references(battle._extract_cards_from_strategy(strategy))
        source_path, factory_name = _strategy_source(loader, display_name)
        rendered.append(
            RenderedStrategy(
                display_name=display_name,
                slug=strategy_slug(display_name),
                strategy=strategy,
                source_path=source_path,
                factory_name=factory_name,
                references={
                    "Kingdom Cards": refs.kingdom_cards,
                    "Events": refs.events,
                    "Projects": refs.projects,
                    "Ways": refs.ways,
                    "Landmarks": refs.landmarks,
                    "Allies": refs.allies,
                },
            )
        )

    return rendered


def _page_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --border: #d8dde6;
      --text: #1f2937;
      --muted: #667085;
      --header: #f3f5f8;
      --row: #fbfcfe;
      --accent: #255e8f;
    }}
    body {{
      color: var(--text);
      font-family: Arial, sans-serif;
      line-height: 1.4;
      margin: 32px auto;
      max-width: 1120px;
      padding: 0 24px;
    }}
    a {{ color: var(--accent); }}
    h1 {{ margin-bottom: 4px; }}
    h2 {{ border-bottom: 1px solid var(--border); margin-top: 32px; padding-bottom: 6px; }}
    .muted, .empty {{ color: var(--muted); }}
    .meta {{
      display: grid;
      gap: 8px 20px;
      grid-template-columns: max-content 1fr;
      margin: 20px 0;
    }}
    .meta dt {{ color: var(--muted); font-weight: bold; }}
    .meta dd {{ margin: 0; }}
    table {{
      border-collapse: collapse;
      margin: 12px 0 24px;
      width: 100%;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 7px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: var(--header); }}
    tr:nth-child(even) td {{ background: var(--row); }}
    td:first-child {{ width: 54px; }}
    .search {{
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 16px;
      margin: 18px 0;
      padding: 9px 11px;
      width: min(460px, 100%);
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def render_strategy_page(item: RenderedStrategy, *, index_href: str = "index.html") -> str:
    strategy = item.strategy
    references = "".join(
        f"<dt>{escape(label)}</dt><dd>{_reference_list(values)}</dd>"
        for label, values in item.references.items()
    )
    body = f"""
<p><a href="{escape(index_href)}">Strategy index</a></p>
<h1>{escape(item.display_name)}</h1>
<p class="muted">{escape(getattr(strategy, "description", "") or "No description.")}</p>

<dl class="meta">
  <dt>Internal Name</dt><dd>{escape(getattr(strategy, "name", ""))}</dd>
  <dt>Version</dt><dd>{escape(getattr(strategy, "version", ""))}</dd>
  <dt>Source</dt><dd>{escape(item.source_path or "Unknown")}</dd>
  <dt>Factory</dt><dd>{escape(item.factory_name or "Unknown")}</dd>
  {references}
</dl>

<h2>Gain Priority</h2>
<table>
  <tr><th>#</th><th>Card or Event</th><th>Condition</th></tr>
  {_priority_rows(getattr(strategy, "gain_priority", []))}
</table>

<h2>Action Priority</h2>
<table>
  <tr><th>#</th><th>Card</th><th>Condition</th></tr>
  {_priority_rows(getattr(strategy, "action_priority", []))}
</table>

<h2>Trash Priority</h2>
<table>
  <tr><th>#</th><th>Card</th><th>Condition</th></tr>
  {_priority_rows(getattr(strategy, "trash_priority", []))}
</table>

<h2>Treasure Priority</h2>
<table>
  <tr><th>#</th><th>Card</th><th>Condition</th></tr>
  {_priority_rows(getattr(strategy, "treasure_priority", []))}
</table>

<h2>Way Policy</h2>
<table>
  <tr><th>#</th><th>Card</th><th>Way</th><th>Condition</th></tr>
  {_way_rows(getattr(strategy, "way_policy", []) or [])}
</table>
"""
    return _page_shell(f"{item.display_name} Strategy", body)


def render_strategy_index(items: list[RenderedStrategy]) -> str:
    rows = []
    for item in items:
        strategy = item.strategy
        refs = item.references["Kingdom Cards"]
        rows.append(
            "<tr class=\"strategy-row\">"
            f"<td><a href=\"{escape(item.slug)}.html\">{escape(item.display_name)}</a></td>"
            f"<td>{escape(getattr(strategy, 'name', ''))}</td>"
            f"<td>{escape(getattr(strategy, 'description', '') or '')}</td>"
            f"<td>{_reference_list(refs)}</td>"
            f"<td>{escape(item.source_path or 'Unknown')}</td>"
            "</tr>"
        )

    body = f"""
<h1>Strategy Index</h1>
<p class="muted">Generated from registered strategy objects. Regenerate this directory after changing strategy code.</p>
<input class="search" id="strategy-search" type="search" placeholder="Search strategies">
<table id="strategy-table">
  <tr><th>Strategy</th><th>Internal Name</th><th>Description</th><th>Kingdom Cards Used</th><th>Source</th></tr>
  {''.join(rows)}
</table>
<script>
const search = document.getElementById('strategy-search');
const rows = Array.from(document.querySelectorAll('.strategy-row'));
search.addEventListener('input', () => {{
  const query = search.value.toLowerCase();
  for (const row of rows) {{
    row.style.display = row.innerText.toLowerCase().includes(query) ? '' : 'none';
  }}
}});
</script>
"""
    return _page_shell("Strategy Index", body)


def render_strategy_pages(
    output_dir: Path,
    *,
    names: Iterable[str] | None = None,
    loader: StrategyLoader | None = None,
) -> list[Path]:
    """Write strategy HTML pages and return created paths."""

    output_dir.mkdir(parents=True, exist_ok=True)
    items = collect_rendered_strategies(loader, names=names)
    written = []

    index_path = output_dir / "index.html"
    index_path.write_text(render_strategy_index(items), encoding="utf-8")
    written.append(index_path)

    for item in items:
        path = output_dir / f"{item.slug}.html"
        path.write_text(render_strategy_page(item), encoding="utf-8")
        written.append(path)

    return written
