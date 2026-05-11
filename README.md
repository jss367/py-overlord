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

