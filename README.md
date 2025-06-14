# py-overlord

To battle strategies:

python -m dominion.simulation.strategy_battle ChapelWitch BigMoney --games 2

Pass `--use-shelters` to start each player with Necropolis, Hovel and
Overgrown Estate instead of three Estates.

To run every strategy against each other and produce a leaderboard:

```
python compare_all_strategies.py --games 5
```

The leaderboard will be written to `leaderboard.md` by default.
