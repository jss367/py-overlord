# Calibration suite: boards with known answers

## Why this exists

When an evolved champion is mediocre, four very different things can be wrong,
and they need different fixes:

1. **Simulator bug** — a card rule is wrong, so the board plays differently
   than real Dominion (see the Hyderabad Exile bug, where one wrong rule
   flipped a seed strategy from 4% to 93% vs Big Money).
2. **Policy ceiling** — the priority-list strategy language or a hardcoded
   computer-player hook cannot
   represent the play the board demands.
3. **Search failure** — genetic search never finds a genome the strategy
   language could express.
4. **Evaluation noise** — the fitness signal was too noisy to rank candidates.

Until now the repo had no way to tell these apart, because every result was
measured against opponents the pipeline itself produced. The calibration
suite adds an external reference: boards where the Dominion community
established the best (or near-best) strategy years ago, paired with clean
hand-written encodings of those strategies.

## The boards

All boards live in `boards/calibration/`. Most pair one strong kingdom card
with deliberately weak support (Big Money plus one focal kingdom card),
because those have the most
settled community answers.

| Board | Known best | The known answer |
|---|---|---|
| `smithy_bm` | Double Smithy | Big Money plus two Smithies beats straight Big Money (classic simulation result) |
| `witch_bm` | Double Witch | Witch money crushes Big Money on support-free boards |
| `chapel_witch` | Chapel Witch Classic | Chapel thinning into Witch beats unthinned Witch money |
| `gardens_workshop` | Gardens Workshop Rush | Workshop-gains-Gardens rush beats money on weak-money boards |
| `wharf_bm` | Big Money Wharf | Big Money with Wharf was the strongest classic focal-card strategy |
| `rebuild_duchy` | Rebuild Rush | Rebuild/Duchy (no Gold) beats money strategies outright |
| `jack_bm` | Double Jack | Double Jack was the Isotropic-era benchmark |
| `mountebank_bm` | Mountebank Money | Mountebank money is a standard strong baseline |
| `courtyard_bm` | Courtyard Money | Two Courtyards on $2–4 hands beats straight Big Money |
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
  `chapel_witch` or `gardens_workshop` but not on the focal-card boards points at
  representation/play-skill limits (trash policy, gainer play) rather than
  general search failure.

When comparing pipeline changes, run evolve mode before and after with the
same settings and compare mean gaps; the JSON output is meant for exactly
that kind of regression tracking.

## First results (2026-07-04)

Baseline run: population 30, generations 30, games-per-eval 15, 400
confirmation games, out-of-the-box trainer settings (Big Money panel).
**Mean gap: 4.7pp; champions behind on 4 of 10 boards.** Full tables in
`reports/calibration/evolve.md` and `sanity.md`. The failures split into
exactly the categories the suite was designed to separate:

- **Representability failure — `rebuild_duchy` (32.8%).** The Rebuild rush
  needs "buy Duchy over Gold, unconditionally"; the structured genome's
  greening block always gates Duchy behind `provinces_left <= 3..6` (both at
  init and in the re-gate vocabulary in `structured_genome.py`), so the
  known-best plan is outside the search space entirely. Fix: widen the
  greening-gate vocabulary. `chapel_witch` (44.0%) is likely related — the
  vocabulary has no "buy exactly one Chapel on turns 1-2" shape (turn-gated
  picks exist but the trainer must find cap-1 + early-turn + Chapel jointly).
- **Objective failure — `witch_bm` (40.5%), `smithy_bm` (41.8%).** Both
  archetypes are fully representable (a capped kingdom pick over a money
  backbone), yet champions trained against the Big Money panel converge to
  something that beats Big Money without matching the tuned focal-card mirror.
  Fixed weak panels give no gradient toward mirror-optimal play; this is the
  motivation for a coevolution / champion-pool outer loop.
- **Legitimate wins — `gardens_workshop` (93.2%), `courtyard_bm` (57.8%).**
  On the Gardens board genetic search found a genuinely better plan than the
  community archetype: play money, contest the Gardens pile from the money
  deck, and win the long game on Provinces. Hand-buffed rush variants
  (uncapped Workshops, earlier Estates) still lose ~90% to the champion's
  saved genome. The known-best label stays as a reference, but the community
  answer is not the best strategy on this exact board in this simulator.

## Caveats

- The known-best strategies are strong reference points, not proofs of
  optimality. A champion beating one is a good sign, not a guarantee.
- Known-best play still flows through the same computer-player hooks as everyone
  else (e.g. Jack of All Trades' hardcoded trash/discard choices). A weak hook
  can affect both strategies, but not necessarily equally: the strategy that
  buys or invokes the card more often may be hurt more. Interpret sanity-mode
  margins involving such hooks with caution.
- 400 games resolves ~5pp differences; use 1000+ for finer comparisons.

## Representation update (2026-07-10)

The structured search representation now uses typed opening, build, economy,
greening, and endgame modules. The Rebuild plan, an exact early single-card
opening, and score-aware third-pile endings are directly representable and
covered by tests. See `docs/strategy-search-architecture.md`.

The first-results table above remains the historical baseline. It should not
be overwritten by a small smoke run; the next comparable run must use the same
30-individual, 30-generation, 15-game evaluation budget and 400 confirmation
games.
