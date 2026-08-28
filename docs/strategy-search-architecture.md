# Strategy search architecture

The solver searches complete strategic plans rather than treating an ordered
buy list as the strategy itself. Gameplay still consumes ordinary priority
rules, but search operates on typed modules and compiles them into those rules.
This keeps saved strategies readable and compatible with the simulator while
making genetic edits strategically meaningful.

## Typed strategy modules

`dominion/simulation/strategic_genome.py` defines the current modules:

- opening targets, including an exact copy count and opening turn window;
- build targets, including copy count, timing, dependencies, and their
  priority relative to Province and Duchy;
- economy policy, including deliberate no-Gold rushes;
- Province, Duchy, and Estate greening policy;
- score-aware third-pile endings;
- trashing thresholds;
- action and Treasure play order.

The compiler attaches the typed genome to an ordinary `BaseStrategy` as
`_strategic_genome`. Semantic mutation changes one of the modules and then
recompiles the phenotype. Semantic crossover exchanges whole modules between
parents. Hand-written or older generated strategies without typed metadata
continue through the previous structured-list operators.

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

## Next search layer: adversarial league training

The next architectural slice replaces a fixed opponent average with an
iterative league:

1. optimize separate strategic archetypes;
2. build their complete cross-play matrix;
3. search for a counterstrategy to the current league leader or mixture;
4. retain counters that expose a statistically meaningful weakness;
5. train subsequent candidates against a weighted league mixture;
6. stop only after repeated counter searches fail to find an exploit.

League evaluation should report both mixture win rate and the candidate's
worst supported matchup. Historical champions remain useful regression
opponents, but they are not a substitute for actively generated counters.

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
