# Reflective strategy search with GEPA

This experiment adds an LLM-proposed strategy seed to the existing genetic
trainer. GEPA (Genetic-Pareto) reads simulator feedback and evolves the JSON
representation of `StrategicGenome`. It does not generate executable Python or
call a model during gameplay. The implementation uses the
[official GEPA adapter interface](https://github.com/gepa-ai/gepa).

The [published Oslo subscription pilot](../reports/strategies/oslo-reflective-strategy-search-pilot.html)
contains the completed comparison, recorded evidence, and uncertainty.
The [policy coverage audit](../reports/strategies/oslo-strategic-genome-coverage.html)
records the schema 2 reference-equivalence checks.
The [five-seed shared-budget benchmark](../reports/strategies/oslo-reflective-shared-budget-benchmark.html)
records the completed larger comparison, its primary uncertainty, and opponent-specific outcomes.
The [saved-candidate follow-up](../reports/strategies/oslo-reflective-proposals-and-final-recommendations.html)
compares original proposals, final assisted recommendations, and controls on a separate
fresh shuffle block without making model calls or selecting new recommendations.

These are historical October 2026 studies. Their recorded engine used the old
tie/capped-game behavior. The complete pre-integration code is preserved at
`2e1479e32e44dce93585733b97bc6afa48a7c885`; check out that commit to reproduce
those exact inputs with the trusted local artifacts. The current implementation
uses main's explicit outcome contract. The saved-candidate runner deliberately
rejects old checkpoints when their simulator fingerprint differs from the
current tree. Updating this PR to main did not rerun or relabel historical results.

## Install and run

Use Python 3.14 and install the optional dependencies:

```bash
python -m pip install -e '.[gepa]'
PYTHONPATH=. python scripts/reflective_evolve.py \
  --board boards/oslo.txt \
  --reflection-backend codex \
  --reference "Oslo Workers Village Magnate Refined Engine" \
  --reference "Oslo Workers Village Magnate Multi Colony Engine" \
  --seeds 21 22 23 24 25 --max-metric-calls 20 \
  --population 30 --generations 30 --train-games 10 \
  --validation-games 100 --test-games 400 --workers 12 \
  --search-game-budget 60000 \
  --output .context/reflective-oslo-comparison
```

The default `codex` backend uses your existing Codex CLI ChatGPT sign-in and
subscription allowance. Install Codex and run `codex login` if needed. API keys
are not required. The adapter checks for ChatGPT authentication, removes API
credentials and routing overrides only from the child environment, ignores
custom CLI configuration, and runs an ephemeral session in an empty read-only
directory. It sends the full reflection task on stdin and saves the final JSON
response. It never reads or copies OAuth tokens. Existing login/configuration
and parent environment variables remain unchanged. The optional
`--reflection-model` overrides the CLI's default model. Subscription usage
limits still apply. See [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
and [authentication](https://learn.chatgpt.com/docs/auth).

For paid API access instead, install `python -m pip install -e '.[gepa-api]'`
and pass `--reflection-backend api --reflection-model openai/gpt-5.4-mini`
(or another LiteLLM provider/model identifier). Set that provider's environment
variable with working generation access and account credit. A successful
model-listing request alone does not establish generation access. Either
backend fails the experiment on provider errors; failures cannot silently
produce a comparison with an unchanged seed.

For a small integration pilot, use one seed, 8 individuals, 2 generations,
4 training games, 20 validation games, and 40 test games per opponent. That
budget checks execution; it cannot establish a strength improvement. Use a new
output directory for every experiment. No previous run is overwritten.

## What is compared

Both arms use the same board, opponents, search seed, genetic trainer settings,
and board-derived engine seeds. The control also receives the initial typed
engine plan. The treatment additionally receives the seed proposed by GEPA.
The editable plan comes from board capabilities rather than copying a reference
champion. Strong references remain opponents. The separate coverage audit
hand-encodes references to test representability; those plans are not injected
automatically into search.

Behaviorally duplicate seeds are removed. If GEPA returns an existing seed,
both arms receive identical initial seeds; an unchanged proposal cannot create
an apparent gain simply by injecting another clone or changing seeding order.

GEPA receives one evaluation case per opponent and split. Cases contain complete
seat-swapped pairs with identical initial RNG seeds; train, validation, and test
have distinct seed blocks. A shared seed does not guarantee identical shuffles
after policies make different decisions. Evaluation restores the caller's RNG,
so simulator work cannot alter the subsequent genetic mutation stream.

GEPA retains candidates by per-opponent validation performance. Its default best
candidate uses a plain mean, so this adapter selects the injected seed with the
existing league aggregation: half panel mean, half mean of the worst half.
Each genetic arm then chooses among its starting strategies and confirmed
champion on a shared validation panel. Both recommendations are saved before
any held-out games. Test results do not update either recommendation.

`--search-game-budget` gives each arm the same hard simulation allowance per
search seed. GEPA's completed games count against the assisted arm. Both arms
train against the same fixed reference panel, without hall-of-fame additions.
Before a generation starts, the trainer reserves its full screen, refine,
confirmation and possible rebase cost, plus a minimum final selection reserve.
It stops before a generation that cannot fit; `--generations` is a ceiling.

After training, each arm spends its remaining allowance on the same number of
seat-balanced selection games per unique candidate and opponent. The minimum
is `--validation-games` per opponent. Additional pairs use the common validation
seed block, with all options within an arm receiving equal samples. At most
one such all-option pair block remains unused, and actual completed games and
unused allowance are reported. Thus the caps are equal and expenditure is
nearly equal, rather than padded with discarded games. The arms can complete
different generation counts and use different selection sample sizes. Fresh
test panels and the direct matchup have fixed, separately counted costs; the
direct matchup uses a separate random block in this mode.

Without this flag, the **earlier extra-compute comparison** remains available:
GEPA adds simulation work, and candidate-specific confirmation costs can differ.
It retains the pilot's dynamic league and seed conventions. The prior direct
matchup reused the first panel opponent's random seed block; those game results
cannot be treated as independent of that opponent's panel games.
Reports include actual completed genetic games, GEPA games, selection games,
held-out games, elapsed time, tokens, and the billing mode. API runs include
estimated API dollars; subscription runs use a null API estimate and report
CLI request counts and cached input tokens. A shared game allowance does not
equalize model tokens or wall-clock cost. Use multiple search seeds and independent
matchups before claiming a gain; compare against the repository's documented
calibration budget when making strength claims.

## Feedback, boundaries, and budgets

Reflection receives board setup, card capabilities, matchup win rates and score
margins, rule firings, and a representative loss with a bounded real game-log
excerpt. Excerpts include hand/resource context, recent turn summaries, and the
final scoring/deck breakdown. One loss is not a causal diagnosis; simulator
evaluation must establish whether a proposed change helps.

The schema accepts ordered opening/build targets, copy counts, timing windows,
dependencies, economy, greening, endgame, trashing, and Action/Treasure order.
Malformed JSON, unknown fields, wrong types, unavailable cards, wrong card
roles, and out-of-range values get negative feedback without playing games.
Simulator errors propagate rather than being converted to poor strategy scores.

Schema 2 adds first-gain openings, counted dependencies, purchase deck-count
balancing, Colony resource gates with commitment/fallback timing, Colony-or-turn
Province timing, conditional Treasure retention, balanced Anvil gains, and
multiplier payload protection. Genetic initialization, mutation and crossover
can reach these fields; export/reload and deduplication preserve them. The two
strong Oslo reference configurations now reproduce their recorded decisions
without inheriting custom hooks. Balanced gains are currently supported for
Anvil; other custom tactics may still lie outside the JSON space.

Use `--genome-schema 1` to retain the older pilot's fields and genetic random
stream. Saved schema 1 JSON remains strictly readable; omitted new policies
receive neutral defaults. A supplied `--seed-genome` must match the chosen
schema. Schema 2 is the default for new experiments.

The optional `card_decision_policies` mapping also round-trips when present,
using the trainer's finite policy vocabularies and strict value validation.
Historical JSON without this field retains `None`; generated schemas omit a
neutral mapping. This preserves current genetic mutations without rewriting
the stored historical plans.

```bash
PYTHONPATH=. python scripts/audit_oslo_genome.py \
  --pairs 25 --seed 1729 --output .context/oslo-policy-coverage
```

`--max-metric-calls` is a hard **per-seed** case-evaluation cap; each call plays
the requested games against one opponent. The adapter reserves an entire
parent/child comparison plus a full validation panel before another iteration,
so it may stop below the cap. Invalid plans count toward the cap. The minimum
budget is twice the opponent count plus two. This cap excludes the later
genetic search and final evaluation, whose costs are reported separately.

For the API backend, `--max-reflection-cost` defaults to a per-seed $0.50 **estimated stop threshold**.
It is checked between iterations and a single request may cross it. Model-price
estimates come from LiteLLM, not an account billing statement. Reflection uses
at most 4,096 output tokens per API request and disables provider retries.
Subscription runs use the evaluator-call cap and a default 300-second timeout
per CLI request (`--reflection-timeout`); the dollar threshold does not apply.

Scoring follows main's shared outcome contract: compare victory points, then
fewer turns; fully tied natural games give each player half credit. Safety-capped
games give neither player credit and retain a distinct `truncated` outcome.
The historical adapter key `win_rate` now contains mean win share over all games,
including capped games in its denominator. Rows preserve `won`, `win_share`,
`result`, and `termination_reason`, and panels retain explicit outcome counts.
Mean score margin excludes capped games. The published October evidence retains
its original boolean-win columns and scoring and is clearly marked historical.

## Compare saved proposals without model access

With the trusted local checkpoints from a completed experiment, run this diagnostic with:

```bash
PYTHONPATH=. python scripts/compare_saved_reflective_candidates.py \
  --source .context/oslo-reflective-shared-budget-benchmark \
  --games 1000 --workers 12 \
  --output .context/oslo-saved-candidate-reproduction
```

The runner freezes every candidate before evaluation, verifies the simulator fingerprint,
rejects overlap with saved source-game seeds, and records a seed-level analysis plan before
playing new games. Identical compiled policies share results. Its output preserves all
outcomes and checkpoint hashes, and includes local candidate/opponent snapshots. It requires
no GEPA package or provider access. It compares saved candidates, not equally funded
proposal-only and assisted algorithms. Checkpoints are executable pickle data; only use
trusted locally generated experiments.

To publish completed output, render a source guide and evidence, register its metadata in
`CURATED_STRATEGY_GUIDES`, then run the catalog renderer:

```bash
PYTHONPATH=. python scripts/render_saved_reflective_comparison.py \
  --comparison .context/oslo-saved-reflective-candidate-comparison/comparison.json \
  --board-name Oslo \
  --guide dominion/reporting/curated_strategy_guides/oslo-reflective-proposals-and-final-recommendations.html \
  --evidence reports/research/oslo-reflective-proposals-and-final-recommendations.json
PYTHONPATH=. python scripts/render_catalog.py
```

## Artifacts and verification

The experiment manifest stores the command, board, settings, dependency versions,
and simulation-input fingerprint. Each seed saves the original and selected JSON
plans, GEPA lineage/validation scores, genetic selection results, trusted local
strategy checkpoints, per-game seeds/scores/seats, reflection game logs, and the
final summary. Subscription runs also save each CLI prompt, final response,
event stream, diagnostics, and usage metadata. Load pickle checkpoints only
from trusted experiments.

```bash
python -m pytest -q tests/test_reflective_strategy_search.py \
  tests/test_codex_reflection.py tests/test_genetic_trainer.py tests/test_parallel_games.py \
  tests/test_simulation_budget.py tests/test_saved_reflective_candidates.py
python -m ruff check .
```

With the optional dependencies installed, the tests also exercise the actual
GEPA engine and Dominion simulator using a deterministic test proposer without
network calls. That test verifies the integration and budget; it is not a GEPA
strength experiment. Publish any real strategy search findings as an HTML guide
through the strategy catalog, as required by `AGENTS.md`.
