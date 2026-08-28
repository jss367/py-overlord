# Notes for agents working in this repo

## There is no strategy registry to update

`StrategyLoader` (`dominion/strategy/strategy_loader.py`) is the single index of
strategies. It discovers every `create_*() -> EnhancedStrategy` factory in
`dominion/strategy/strategies/` and `generated_strategies/` at import time, and
everything downstream — `StrategyBattle`, `compare_all_strategies.py`, the HTML
catalog — reads from it.

To add a strategy, drop a module in one of those directories with a
`create_<name>() -> EnhancedStrategy` factory (the return annotation is required;
that is how the loader finds it). Do not add a lookup table anywhere else.

## The board/strategy catalog is generated, never committed

`PYTHONPATH=. python scripts/render_catalog.py` rebuilds
`reports/strategies/index.html`, `reports/boards/index.html`, and one page per
strategy and board. It runs in a couple of seconds.

`reports/` is gitignored. Do not force-add catalog pages: a committed snapshot
goes stale the moment a strategy is added, and a committed index whose target
pages are missing is worse than no index. Regenerate on demand instead.

## Checks before opening a PR

```
pytest -q
python -m ruff check . --select E9,F63,F7,F82
```
