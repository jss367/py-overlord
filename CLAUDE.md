# Notes for agents working in this repo

## Publish written strategy guides as HTML

Follow the [strategy publishing instructions in AGENTS.md](AGENTS.md#publish-strategy-guides-as-html).
User-facing strategy recommendations and search findings must be HTML guides,
with sources in `dominion/reporting/curated_strategy_guides/`, registered in
`CURATED_STRATEGY_GUIDES`, and published in `reports/strategies/` by catalog
regeneration. Existing Markdown strategy writeups are legacy material, not the
format to use for new guides. Developer documentation may remain Markdown.

## There is no strategy registry to update

`StrategyLoader` (`dominion/strategy/strategy_loader.py`) is the single index of
strategies. It discovers every `create_*() -> EnhancedStrategy` factory in
`dominion/strategy/strategies/` and `generated_strategies/` at import time, and
everything downstream — `StrategyBattle`, `compare_all_strategies.py`, the HTML
catalog — reads from it.

To add a strategy, drop a module in one of those directories with a
`create_<name>() -> EnhancedStrategy` factory (the return annotation is required;
that is how the loader finds it). Do not add a lookup table anywhere else.

## Keep the committed board and strategy catalog current

`PYTHONPATH=. python scripts/render_catalog.py` rebuilds
`reports/strategies/index.html`, `reports/boards/index.html`, and one page per
strategy and board. It runs in a couple of seconds.

The generated pages under `reports/strategies/` and `reports/boards/`, plus
`reports/index.html`, are committed. Regenerate them whenever a strategy or board
changes. These catalog directories are renderer-owned; regeneration removes
obsolete HTML pages. Put custom reports elsewhere under `reports/`.

Catalog regeneration preserves tournament standings and their embedded result
data in `reports/strategies/leaderboard.html`, and rebuilds card usage ranks from
those results. Do not restore the old leaderboard after rendering: that would
discard updated presentation and freshness notices. Simulation input changes
mark results as outdated; guide and presentation edits do not. Legacy standings
are migrated with unknown freshness, never silently treated as a new tournament.

Run `python scripts/install_catalog_hook.py` once to enable automatic updates.
The pre-commit hook builds from staged sources, updates changed reports, and
stops so you can review and stage them. It does not stage files or overwrite
unstaged report edits. Existing hooks are preserved. Shared Git hook directories
also cover other worktrees whose branches contain the hook script.

`python scripts/check_catalog.py` compares a clean regeneration seeded with saved
tournament results against every committed catalog page, including standings
and card ranks. CI runs the same check and rejects stale catalogs.

## Checks before opening a PR

```
pytest -q
python -m ruff check . --select E9,F63,F7,F82
```
