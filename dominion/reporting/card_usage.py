"""Static, sortable card usage report for the registered strategy catalog."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re
from statistics import median
from typing import Any, Mapping

from dominion.cards.registry import get_all_card_names, get_card
from dominion.reporting.strategy_pages import (
    RenderedStrategy,
    _card_chip,
    _leaderboard_sort_key,
    _page_shell,
)
from dominion.simulation.strategy_battle import BASIC_CARDS, StrategyBattle
from dominion.strategy.strategy_loader import StrategyLoader


# Board extraction treats conditional base piles as references; the report's
# visibility filter groups them with the other basic and starting cards.
REPORT_BASIC_CARDS = BASIC_CARDS | {"Colony", "Platinum", "Potion"}


@dataclass(frozen=True)
class CardUsage:
    name: str
    strategies: tuple[RenderedStrategy, ...]
    ranks: tuple[int, ...]

    @property
    def median_rank(self) -> float | None:
        return median(self.ranks) if self.ranks else None


def collect_card_usage(
    strategies: list[RenderedStrategy],
    results: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    loader: StrategyLoader | None = None,
) -> list[CardUsage]:
    """Count explicit priority/way references once per card and strategy.

    Ranks are ordinal positions using exactly the leaderboard's ordering.
    Unranked strategies count toward usage but do not enter the median.
    """
    loader = loader or StrategyLoader()
    ranks = {}
    for rank, (name, _) in enumerate(
        sorted((results or {}).items(), key=_leaderboard_sort_key), 1
    ):
        resolved = loader.get_display_name(name) or name
        ranks.setdefault(resolved, rank)

    members: dict[str, dict[str, RenderedStrategy]] = {
        get_card(name).name: {} for name in get_all_card_names()
    }
    with StrategyBattle(log_frequency=0) as battle:
        for item in strategies:
            for reference in battle._extract_cards_from_strategy(item.strategy):
                try:
                    name = get_card(reference).name
                except ValueError:
                    # Landscapes and generic targets such as "Treasure" are not cards.
                    continue
                members[name][item.display_name] = item

    rows = []
    for name, entries in members.items():
        ordered = tuple(sorted(entries.values(), key=lambda item: item.display_name.casefold()))
        rows.append(CardUsage(name, ordered, tuple(
            ranks[item.display_name] for item in ordered if item.display_name in ranks
        )))
    return sorted(rows, key=lambda row: (-len(row.strategies), row.name.casefold()))


def render_card_usage(
    strategies: list[RenderedStrategy],
    results: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    index_href: str = "index.html",
    leaderboard_href: str | None = "leaderboard.html",
    strategy_link_prefix: str = "",
    context_label: str = "a cross-board round robin",
    loader: StrategyLoader | None = None,
) -> str:
    rows = collect_card_usage(strategies, results, loader=loader)
    total = len({item.display_name for item in strategies})
    used = sum(bool(row.strategies) for row in rows)
    markup = []
    for row in rows:
        count = len(row.strategies)
        share = 100 * count / total if total else 0
        rank_value = row.median_rank
        links = "".join(
            f'<li><a href="{escape(strategy_link_prefix.rstrip("/") + "/" if strategy_link_prefix else "")}'
            f'{escape(item.slug)}.html">{escape(item.display_name)}</a></li>'
            for item in row.strategies
        )
        details = (
            f'<details><summary>View {count} strategies</summary><ul>{links}</ul></details>'
            if count else '<span class="muted">No strategies</span>'
        )
        markup.append(
            f'<tr data-basic="{str(row.name in REPORT_BASIC_CARDS).lower()}">'
            f'<td data-sort="{escape(row.name)}">{_card_chip(row.name)}</td>'
            f'<td data-sort="{count}"><strong>{count}</strong></td>'
            f'<td data-sort="{share}">{share:.1f}%</td>'
            f'<td data-label="Median strategy rank" data-sort="{rank_value if rank_value is not None else ""}">'
            f'{format(rank_value, "g") if rank_value is not None else "—"}</td>'
            f'<td data-label="Ranked strategies" data-sort="{len(row.ranks)}">{len(row.ranks)}</td>'
            f'<td>{details}</td></tr>'
        )
    leaderboard_nav = (
        f'<a href="{escape(leaderboard_href)}">Leaderboard</a>' if leaderboard_href else ""
    )
    rank_note = (
        f'Ranks come from <strong>{escape(context_label)}</strong>. '
        'Median uses only ranked strategies; lower is better. '
        'Positions and tie ordering match the leaderboard (win rate, wins, losses, then name).'
        if results else
        'No tournament results yet. Median ranks are unavailable until you run '
        '<code>python compare_all_strategies.py</code>.'
    )
    headings = "".join(
        f'<th scope="col" aria-sort="{"descending" if key == 1 else "none"}">'
        f'<button type="button" data-column="{key}" data-numeric="{str(key != 0).lower()}">'
        f'{label}<span aria-hidden="true"> {"↓" if key == 1 else "↕"}</span></button></th>'
        for key, label in enumerate(["Card", "Strategies", "Share of strategies", "Median strategy rank", "Ranked strategies"])
    )
    body = f"""
<nav><a href="{escape(index_href)}">Strategy index</a>{leaderboard_nav}</nav>
<header class="hero">
  <p class="eyebrow">Dominion strategy catalog</p>
  <h1>Card Strategy Usage</h1>
  <p class="hero-description">Explore which cards appear in the most and least strategies.</p>
  <p><strong>{total}</strong> registered strategies · <strong>{used}</strong> referenced cards · <strong>{len(rows) - used}</strong> unused cards</p>
</header>
<section class="section">
  <p>Each card counts once per strategy that explicitly names it in a gain, action, trash, exile,
  treasure priority, or Way rule. References in conditions and custom decision code, automatic gains,
  and curated guides are excluded. A reference does not mean the card was bought or helped win.</p>
  <p id="card-rank-note">{rank_note} The ranked-strategy count shows the sample behind each median.</p>
  <div class="usage-controls">
    <div><label for="card-search">Find a card or strategy</label><br>
    <input class="search" id="card-search" type="search" placeholder="Search cards or strategies"></div>
    <label><input id="include-basic" type="checkbox"> Include basic and starting cards</label>
    <label><input id="unused-only" type="checkbox"> Only unused cards</label>
  </div>
  <p id="card-count" role="status" aria-live="polite"></p>
  <div class="table-scroll">
    <table id="card-usage-table">
      <caption>Card usage across {total} registered strategies. Select a column heading to sort.</caption>
      <thead><tr>{headings}<th scope="col">Matching strategies</th></tr></thead>
      <tbody>{''.join(markup)}</tbody>
    </table>
  </div>
  <p id="card-empty" hidden>No cards match these filters.</p>
  <noscript>Enable JavaScript to sort and filter this table.</noscript>
</section>
{_SCRIPT}
"""
    return _page_shell("Card Strategy Usage", body, extra_styles=_STYLES)


def normalize_card_usage_for_comparison(html: str) -> str:
    """Remove only tournament-specific fields from our generated markup."""
    html = re.sub(
        r'(<p id="card-rank-note">).*?(</p>)', r'\1\2', html, flags=re.DOTALL,
    )
    return re.sub(
        r'<td data-label="(Median strategy rank|Ranked strategies)" data-sort="[^"]*">.*?</td>',
        r'<td data-label="\1"></td>', html, flags=re.DOTALL,
    )


_STYLES = """
    .usage-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 20px; margin-top: 24px; }
    .usage-controls > div { flex: 1 1 280px; }
    .usage-controls .search { margin-bottom: 0; width: 100%; }
    .table-scroll { overflow-x: auto; padding-bottom: 4px; }
    #card-usage-table { min-width: 880px; }
    #card-usage-table caption { text-align: left; padding: 12px; color: var(--muted); }
    #card-usage-table th button { font: inherit; color: inherit; background: none; border: 0; padding: 0; text-align: left; cursor: pointer; }
    #card-usage-table th button:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
    #card-usage-table td { vertical-align: top; }
    #card-usage-table details { max-width: 300px; }
    #card-usage-table summary { cursor: pointer; color: var(--accent); }
    #card-usage-table ul { padding-left: 18px; }
"""

_SCRIPT = """
<script>
(() => {
  const table = document.getElementById('card-usage-table');
  const body = table.tBodies[0];
  const rows = Array.from(body.rows);
  const buttons = Array.from(table.querySelectorAll('th button'));
  const search = document.getElementById('card-search');
  const basic = document.getElementById('include-basic');
  const unused = document.getElementById('unused-only');
  let column = 1;
  let direction = -1;
  function filter() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    rows.forEach(row => {
      row.hidden = (!basic.checked && row.dataset.basic === 'true') ||
        (unused.checked && Number(row.cells[1].dataset.sort) !== 0) ||
        !row.textContent.toLowerCase().includes(query);
      if (!row.hidden) visible++;
    });
    document.getElementById('card-count').textContent = `${visible} of ${rows.length} cards shown`;
    document.getElementById('card-empty').hidden = visible !== 0;
  }
  buttons.forEach(button => button.addEventListener('click', () => {
    const next = Number(button.dataset.column);
    direction = column === next ? -direction : (next === 1 || next === 2 || next === 4 ? -1 : 1);
    column = next;
    const numeric = button.dataset.numeric === 'true';
    rows.sort((a, b) => {
      const x = a.cells[column].dataset.sort;
      const y = b.cells[column].dataset.sort;
      // Missing ranks stay at the bottom in both directions.
      if (x === '' || y === '') {
        if (x !== y) return x === '' ? 1 : -1;
      }
      const value = numeric ? Number(x) - Number(y) : x.localeCompare(y);
      return direction * value || a.cells[0].dataset.sort.localeCompare(b.cells[0].dataset.sort);
    });
    rows.forEach(row => body.appendChild(row));
    buttons.forEach(other => {
      other.parentElement.setAttribute('aria-sort', other === button ? (direction === 1 ? 'ascending' : 'descending') : 'none');
      other.querySelector('span').textContent = other === button ? (direction === 1 ? ' ↑' : ' ↓') : ' ↕';
    });
  }));
  search.addEventListener('input', filter);
  basic.addEventListener('change', filter);
  unused.addEventListener('change', filter);
  filter();
})();
</script>
"""
