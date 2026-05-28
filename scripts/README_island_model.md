# Island-Model Evolution for Lisbon

Three-stage pipeline for escaping the local-optimum problem on the Lisbon
Colony board (see `boards/lisbon.txt`):

1. **`island_evolve.py`** — one isolated GA per archetype, identical
   hyperparameters, **same fixed opponent panel** across all islands.
2. **`island_tournament.py`** — round-robin between the islands'
   champions to pick the best archetype.
3. **`island_merge.py`** *(optional)* — seed all champions into one
   population and evolve a hybrid stage.

The point of the model is fair comparison. Each archetype's seed is a
distinct theory of the kingdom; without isolated training every theory
would collapse into whatever the current dominant strategy is.

## Why this exists

The previous `Lisbon City Engine` was evolved against a panel that
explicitly excluded Big Money ("too easy to crush"). That deleted the
falsifier — a strategy that builds slowly should *struggle* against a
speed test, and removing the speed test stops the GA from finding that
out. The seed file's own docstring records this:

> "No Big Money on the panel — too easy to crush, doesn't drive learning."

This pipeline includes Big Money in the fixed panel for every island,
and rounds out the panel with `ClerkCollectionColony` as a non-seed
engine baseline.

## Seeds

Six islands, each a different theory:

| Seed | Theory |
|---|---|
| Lisbon Investment Rush | Investment-detonation Colony rush, Watchtower topdecks |
| Lisbon WV Peddler Engine | Workers' Village/Festival/Peddler draw + Expand upgrades |
| Lisbon Watchtower Topdeck | Watchtower reaction as the deck-shaping engine |
| Lisbon Festival BigMoney | Big Money chassis with Festival + Collection |
| Lisbon Gardens Slog | No-Province slog, Gardens + Workers' Village + 3-pile finish |
| Lisbon City Engine | Existing strategy from PR #243 — the control |

Seed source: `dominion/strategy/strategies/lisbon_*.py`.
All are auto-loaded by `StrategyLoader`.

## How to run

The scripts need `PYTHONPATH=.` from the repo root because they import
`dominion.*` directly.

### Smoke test (one minute total)

```bash
PYTHONPATH=. python scripts/island_evolve.py --smoke --parallel
PYTHONPATH=. python scripts/island_tournament.py \
    --manifest generated_strategies/island_champions/<RUN_ID>/manifest.json \
    --games 30 --parallel --include-panel
```

`--smoke` forces population=12, generations=5, games-per-eval=8.
Champions are not informative at this scale; this only validates the
pipeline.

### Real run (multi-hour)

```bash
PYTHONPATH=. python scripts/island_evolve.py \
    --population 30 --generations 60 --games-per-eval 30 --parallel
```

Watch the `island_logs/<RUN_ID>/<seed>/` directories for per-island
training logs. The script prints a summary table at the end and saves
each champion as `generated_strategies/island_champions/<RUN_ID>/<seed>_champion.py`
plus a `manifest.json`.

Then the tournament:

```bash
PYTHONPATH=. python scripts/island_tournament.py \
    --manifest generated_strategies/island_champions/<RUN_ID>/manifest.json \
    --games 400 --parallel --include-panel \
    --output reports/lisbon_island_tournament_<RUN_ID>.md
```

`--include-panel` adds Big Money and ClerkCollectionColony to the
tournament so champions can be compared against the same opponents they
were trained against.

### Optional merged stage

If the tournament shows two or three champions clustered together (e.g.
within 5% of each other), evolve a final hybrid stage:

```bash
PYTHONPATH=. python scripts/island_merge.py \
    --manifest generated_strategies/island_champions/<RUN_ID>/manifest.json \
    --generations 30 --population 40 --games-per-eval 30
```

This seeds one fresh population with every island champion (plus
mutated variants) and evolves against the same fixed panel for another
30 generations. The output is `generated_strategies/island_merged/<RUN_ID>/merged_champion.py`.

Once it finishes, rerun the tournament with the merged champion
added via `--strategies`:

```bash
PYTHONPATH=. python scripts/island_tournament.py \
    --strategies \
      generated_strategies/island_champions/<RUN_ID>/lisbon_investment_rush_champion.py \
      generated_strategies/island_champions/<RUN_ID>/lisbon_wv_peddler_engine_champion.py \
      generated_strategies/island_champions/<RUN_ID>/lisbon_watchtower_topdeck_champion.py \
      generated_strategies/island_champions/<RUN_ID>/lisbon_festival_bigmoney_champion.py \
      generated_strategies/island_champions/<RUN_ID>/lisbon_gardens_slog_champion.py \
      generated_strategies/island_champions/<RUN_ID>/lisbon_city_engine_champion.py \
      generated_strategies/island_merged/<MERGE_RUN_ID>/merged_champion.py \
      "Big Money" "ClerkCollectionColony" \
    --games 400 --parallel
```

## Compute budget estimate

With `--parallel` on a 6+ core machine, a real run is roughly:

- Per island, sequential: population × generations × (games_per_eval / num_panel) games per panel member.
  At pop=30, gens=60, games=30, 2 panel members → 30 × 60 × 30 ≈ 54,000 games.
- 6 islands in parallel → wall time ≈ longest single island.
- Per-game wall time on this codebase is roughly 50–150ms depending on
  the strategy's deck size; figure ~30–90 minutes per island.

Tournament with 8 entries × 28 matchups × 400 games ≈ 11,200 games,
~10–30 min in parallel.

Total wall time for the full pipeline: roughly 1–2 hours on a recent
multi-core MacBook.

## Reading the tournament report

Three blocks of output:

1. **Win-rate matrix** — `row vs col`. A 60% cell at (A, B) means A
   wins 60% of games against B.
2. **Average margin matrix** — `row VP minus col VP`. Useful for
   distinguishing "barely wins" from "crushes."
3. **Average win rate** — single number per strategy, averaged across
   all opponents. This is the ranking.

What you want to see: a non-City-Engine champion at the top of the
average-win-rate table. If City Engine is still #1 after equal
optimization budget, the original "City pile-out is dominant" claim
holds up. If anything else wins, the GA was stuck in a local optimum.

## What "same panel" means and why it matters

Every island evolves against the same `panel = [BigMoney, ClerkCollectionColony]`.
This is **the key methodological fix** — see the docstring of
`scripts/island_evolve.py` for the full rationale.

If you change the panel per island, fitness numbers are no longer
comparable across islands, and the round-robin tournament can't be
trusted to crown the actual best strategy. Resist any urge to "tune
the panel for each archetype."
