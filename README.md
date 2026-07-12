# py-overlord

To battle strategies:

```
python -m dominion.simulation.strategy_battle "Chapel Witch" "Big Money" --games 2
```

Strategy names contain spaces, so be sure to wrap them in quotes when invoking the command line tools.

Pass `--use-shelters` to start each player with Necropolis, Hovel and
Overgrown Estate instead of three Estates.

To run every strategy against each other and produce a leaderboard:

```
python compare_all_strategies.py --games 5
```

The leaderboard will be written to `reports/leaderboard_all.html` by default.
When using `--board`, the default output is
`reports/leaderboard_<board-name>.html`.

Example strategy comparison reports can be generated with the strategy battle
module:

```
python -m dominion.simulation.strategy_battle "Chapel Witch" "Big Money" --games 50 --output reports/chapel_witch_vs_big_money.html
```

If `--output` is omitted, reports are written to the `reports` directory with
an auto-generated filename.

## Board and strategy catalog

Generate linked HTML pages for every board and registered strategy:

```
PYTHONPATH=. python scripts/render_catalog.py
```

The indexes are written to `reports/boards/index.html` and
`reports/strategies/index.html`. Each strategy links to every board that
contains all of its referenced cards and landscapes, and each board links
back to those compatible strategies.

## Calibration suite

`boards/calibration/` pairs boards with community-known best strategies so
the evolution pipeline can be scored against external ground truth instead of
only against itself. Run the fast sanity check (known-best vs Big Money) or
the full benchmark (evolved champion vs known-best):

```
PYTHONPATH=. python scripts/calibration_suite.py --mode sanity --games 400
PYTHONPATH=. python scripts/calibration_suite.py --mode evolve --games 400
```

See `docs/calibration.md` for the board list, sources, and how to read the
gap score.
