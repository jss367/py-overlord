# Repository instructions for agents

Read [CLAUDE.md](CLAUDE.md) for strategy discovery, catalog regeneration, and
validation instructions.

## Publish strategy guides as HTML

Write user-facing strategy recommendations, board guides, and strategy search
findings as HTML. Existing Markdown strategy writeups are legacy documents,
not examples for new work. Runnable strategies remain Python modules.

For a hand-authored guide:

1. Create the HTML source in `dominion/reporting/curated_strategy_guides/` with
   a descriptive filename and title.
2. Add its metadata to `CURATED_STRATEGY_GUIDES` in
   `dominion/reporting/strategy_pages.py`. This registers a written guide;
   runnable strategies are discovered separately by `StrategyLoader`.
3. Run `PYTHONPATH=. python scripts/render_catalog.py` to publish the guide
   under `reports/strategies/` and link it from the strategy index. Follow
   the leaderboard preservation instructions in `CLAUDE.md`.
4. Verify the source and published guide match and the index links to it.
   Link the published HTML in the final response.

Edit the packaged source when updating a guide; catalog regeneration overwrites
the published copy. Do not create a parallel Markdown guide. When converting a
legacy writeup, preserve its findings, evidence, and reproduction commands,
update incoming links, and remove the superseded Markdown after verification.

Markdown remains appropriate for repository instructions, developer documentation,
design plans, and intermediate machine-generated analysis. When presenting that
analysis as a strategy recommendation, publish an HTML guide in the catalog.

See [documentation formats and migration status](README.md#documentation-formats-and-migration-status)
for the remaining legacy documents. Generated strategy detail pages do not
automatically include or replace separately written research narratives.
