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

The leaderboard will be written to `leaderboard.html` by default.

Example reports can be generated using the generic comparison runner:

```
python compare_strategies.py "Chapel Witch" "Big Money" --games 50
```

Reports are written to the `reports` directory.


