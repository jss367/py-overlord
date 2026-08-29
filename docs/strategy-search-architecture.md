# Strategy search architecture

The solver searches complete strategic plans rather than treating an ordered
buy list as the strategy itself. Gameplay still consumes ordinary priority
rules, but search operates on typed modules and compiles them into those rules.
This keeps saved strategies readable and compatible with the simulator while
making genetic edits strategically meaningful.

## Typed strategy modules

`dominion/simulation/strategic_genome.py` defines the current modules:

- opening targets, including an exact copy count and opening turn window;
- build targets, including copy count, start/end timing, dependencies, and
  their priority relative to Province, Duchy, Gold, and Silver;
- economy policy, including deliberate no-Gold rushes;
- Province, Duchy, and Estate greening policy;
- score-aware third-pile endings;
- trashing thresholds;
- action and Treasure play order.

The compiler attaches the typed genome to an ordinary `BaseStrategy` as
`_strategic_genome`. Semantic mutation changes one of the modules and then
recompiles the phenotype. Semantic crossover exchanges whole modules between
parents. Hand-written or older generated strategies are conservatively
promoted when their rule lists round-trip through the typed compiler exactly.
Strategies with unsupported custom or conditional play rules continue through
the previous structured-list operators without behavior changes.

The initial representability targets are all covered directly:

- one Chapel during the first two turns;
- two Rebuilds followed by unconditional Duchies, with Gold disabled;
- an Estate that takes the third pile only when it ends the game without
  falling behind.

## Validation standard

Every community reference strategy in the calibration suite should be
expressible without a custom Python decision hook. A representability test is
required before interpreting a poor calibration result as a search failure.

Small calibration runs are useful for detecting crashes and degenerate search
dynamics, but not for comparing strategy strength. The published baseline used
30 individuals, 30 generations, 15 screening games, and 400 confirmation
games. Comparisons against it must use an equivalent budget and fixed seeds.

## Adversarial league training

Fitness against a fixed opponent average is the binding constraint on this
search, diagnosed twice independently: the BM+X calibration boards stay behind
their community-known best because a Big-Money panel gives no gradient toward
mirror-optimal play, and on Oslo, evolving *from* the winning engine topology
against the weak panel drifted away from it. In both cases the search was not
punished for abandoning a better strategy, because nothing in the panel could
exploit the abandonment.

`dominion/simulation/adversarial_league.py` replaces the hall of fame with a
maintained pool that fixes the three properties that let this happen:

- **Worst-case aggregation.** `aggregate_fitness` blends the panel mean with
  the mean of the worst half (a CVaR — pure `min` over a screening budget is
  mostly deck luck). Under a plain mean, a specialist going 70/40 outscores a
  balanced 55/50; with worst-case weight the ordering flips. The
  `worst_case_weight` trainer knob defaults to 0, preserving legacy behaviour.
- **Retention by difficulty, not recency.** `hall_of_fame[-size:]` keeps the
  newest champions, so a drifting lineage fills the pool with its own drift.
  `AdversarialLeague.prune` evicts the member the champion beats most
  convincingly — an opponent you beat 90% of the time supplies no gradient.
  Members that have never been faced are never evicted.
- **Outside reference opponents.** `build_seeded_league` pre-loads the board's
  assembled engine archetypes (and any named reference strategies), so the
  pool holds topologies the run did not invent and cannot quietly abandon.

`scripts/league_evolve.py` runs the outer double-oracle loop: each round
evolves a best response against the current pool, then promotes it into the
pool. A round whose champion re-derives an existing member is the convergence
signal. `--control` re-runs the identical budget against the hall of fame with
mean aggregation, which is the comparison any claim about the league has to
clear; `--compare` battles the final champion against registered reference
strategies as the gate.

Still unbuilt from the original plan: the full cross-play matrix over pool
members, weighted mixture sampling (opponents are currently faced uniformly),
and a significance test gating retention rather than a point estimate of
difficulty.

## Card capabilities and board-derived engine archetypes

`dominion/analysis/card_capabilities.py` layers a hand-annotated override
table over static card stats, so dynamic cards (Magnate's per-Treasure draw,
Bank's per-Treasure coins, King's Court's triple play) classify into their
real roles instead of reading as all-zero terminals. `KingdomInfo` role
classification and the structured-genome deck caps both consume it; village
and draw caps now reach deep-engine counts (up to 7-8 copies).

`dominion/analysis/engine_archetypes.py` treats engines as a slot-filling
problem over those capabilities: a village and a draw source form the core,
with payload, multiplier, gainer, and +buy support attached when the kingdom
offers them. Each role-complete combination becomes one fully assembled
island seed with aggressive core counts and delayed greening. Seeding the
*finished* engine is the point: partial engines lose to money, so ordinary
selection can never assemble one from mutation (the fitness-valley failure
that made the Oslo board's winning engine unfindable without a human hint).

The rediscovery standard for this layer lives in
`tests/test_engine_archetypes.py::TestOsloRediscovery`: with the strategy
library hidden (`--no-library` in `scripts/island_evolve.py`, or
`reuse_top_k=0`), the board-derived seeds alone must reproduce the
Workers' Village/Magnate topology on Oslo and beat Big Money before any
evolution. Apply the same standard to future boards whose best strategy
the search initially missed: encode the board, hide the library, and
require the enumerator to produce a competitive seed of the right shape.
