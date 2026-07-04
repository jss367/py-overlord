# Calibration suite: boards with known answers

## Why this exists

When an evolved champion is mediocre, four very different things can be wrong,
and they need different fixes:

1. **Simulator bug** — a card rule is wrong, so the board plays differently
   than real Dominion (see the Hyderabad Exile bug, where one wrong rule
   flipped a seed strategy from 4% to 93% vs Big Money).
2. **Policy ceiling** — the priority-list DSL or a hardcoded AI hook cannot
   represent the play the board demands.
3. **Search failure** — the GA never finds a genome the DSL could express.
4. **Evaluation noise** — the fitness signal was too noisy to rank candidates.

Until now the repo had no way to tell these apart, because every result was
measured against opponents the pipeline itself produced. The calibration
suite adds an external reference: boards where the Dominion community
established the best (or near-best) strategy years ago, paired with clean
hand-written encodings of those strategies.

## The boards

All boards live in `boards/calibration/`. Most pair one strong kingdom card
with deliberately weak support ("BM+X" boards), because those have the most
settled community answers.

| Board | Known best | The known answer |
|---|---|---|
| `smithy_bm` | Double Smithy | BM + 2 Smithies beats straight BM (classic sim result) |
| `witch_bm` | Double Witch | Witch money crushes BM on support-free boards |
| `chapel_witch` | Chapel Witch Classic | Chapel thinning into Witch beats unthinned Witch money |
| `gardens_workshop` | Gardens Workshop Rush | Workshop-gains-Gardens rush beats money on weak-money boards |
| `wharf_bm` | Big Money Wharf | BM-Wharf was the strongest classic BM+X |
| `rebuild_duchy` | Rebuild Rush | Rebuild/Duchy (no Gold) beats money strategies outright |
| `jack_bm` | Double Jack | Double Jack was the Isotropic-era benchmark |
| `mountebank_bm` | Mountebank Money | Mountebank-BM is a standard strong baseline |
| `courtyard_bm` | Courtyard Money | 2 Courtyards on $2–4 hands beats straight BM |
| `first_game` | First Game Smithy Militia | Smithy money (+Militia) wins the base-set First Game kingdom |

The known-best strategies are in
`dominion/strategy/strategies/calibration_known_best.py`; the board/strategy
pairing lives in `dominion/analysis/calibration.py` (`CALIBRATION_SUITE`).

## How to run it

**Sanity mode** — validates the simulator + strategy encodings. Each
known-best battles Big Money; every board should PASS (CI lower bound above
50%). A FAIL means the simulator or the encoding is broken on that board —
fix that before trusting any evolution result there.

```bash
PYTHONPATH=. python scripts/calibration_suite.py --mode sanity --games 400
```

**Evolve mode** — the actual benchmark. Runs the genetic trainer on each
board with out-of-the-box settings, then battles the champion against the
known-best for `--games` games:

```bash
PYTHONPATH=. python scripts/calibration_suite.py --mode evolve \
    --population 40 --generations 40 --games-per-eval 20 --games 400
```

Reports (markdown + JSON) land in `reports/calibration/`.

## How to read the numbers

Per board, the **gap** is how many percentage points the champion's win rate
vs the known-best falls below 50. The suite-level number is the **mean gap**:

- **0** — champions tie or beat every known answer. The pipeline is finding
  the good strategies the community found.
- **small (≤5)** — search is close; tuning (budgets, seeds, vocabulary) may
  close it.
- **large on specific boards** — read those boards' verdicts. A big gap on
  `chapel_witch` or `gardens_workshop` but not on the BM+X boards points at
  representation/play-skill limits (trash policy, gainer play) rather than
  general search failure.

When comparing pipeline changes, run evolve mode before and after with the
same settings and compare mean gaps; the JSON output is meant for exactly
that kind of regression tracking.

## Caveats

- The known-best strategies are strong reference points, not proofs of
  optimality. A champion beating one is a good sign, not a guarantee.
- Known-best play still flows through the same AI hooks as everyone else
  (e.g. Jack of All Trades' hardcoded trash/discard choices), so a weak
  hook drags both sides equally in the champion match, but can depress the
  sanity-mode margin vs Big Money.
- 400 games resolves ~5pp differences; use 1000+ for finer comparisons.
