# Training a Dominion agent across kingdoms

This prototype trains **one neural policy across different ten-card kingdoms**.
It supports fifteen cards: Adventurer, Chapel, Council Room, Farm, Festival,
Gardens, Great Hall, Laboratory, Market, Merchant, Moat, Smithy, Village, Witch,
and Woodcutter, plus the ordinary basic cards. It generalizes to new combinations
of those cards; it does not support unseen card implementations or all expansions.

The policy chooses purchases, action order, Treasure order, and optional Chapel
trashing. Revealing Moat remains automatic; blocking Witch has no disadvantage
within this pool. Landscapes, traits, modified setup costs, multiplayer games,
and other card pools are outside this version's scope. The direct game adapter
rejects unsupported kingdoms and setup rules.

## Install and run

From the repository root, install the optional learning dependencies:

```bash
python -m pip install -e '.[rl]'
python -m dominion.rl.general.train \
  --output checkpoints/general-dominion-run \
  --teacher-games 800 --imitation-epochs 15 \
  --iterations 100 --validation-every 20
python -m dominion.rl.general.evaluate \
  checkpoints/general-dominion-run/best.pt \
  --split test --pairs 20 \
  --output .context/general-dominion-evaluation.json
```

Training runs on the CPU with one Torch compute thread. There are no paid API
calls. Each process runs one game at a time because the simulator uses Python's
global random generator. Independent processes may train independently; do not
interleave live environments inside one process.

For a short integration check, use a new output directory and
`--teacher-games 4 --imitation-epochs 1 --iterations 1 --rollout-steps 32
--validation-pairs 1`. This only checks execution, not playing strength.

The training command refuses to overwrite an existing `best.pt`. To continue
learning from a saved policy into a new run, supply `--warm-start PATH`. This
preserves its kingdom splits but starts a fresh optimizer and opponent league;
it is not an exact resumption of the previous random stream. Use a different
`--seed` for an independent continuation. Checkpoint files are ignored by Git.

## What learns

The initial policy imitates a draw-and-money teacher built using the repository's
strategy framework. The teacher adapts purchases to available draw cards and
uses Chapel and Witch when available. Teacher games include the existing Big
Money strategy, the teacher itself, and the existing board-derived engine
archetype builder as opponents. These are teaching signals, not optimal-play
labels. Buying, trashing, playing Actions, and playing Treasures receive balanced
sampling during imitation.

A shared neural card scorer processes printed capabilities, card identity,
supply presence and quantity, and the player's card counts. It combines those
with resources, turn counts, the decision type, and pooled context from the
other cards. There is a separate score for passing. Legal choices mask the
outputs. At inference every purchase, play, and trash choice comes from this
network; the teacher does not override its decisions.
The simulator's heuristic filter against losing endgame purchases is disabled
in learned-agent games, matching the training interface. Both players therefore
face the same unfiltered buy menus.

After imitation, proximal policy optimization (PPO) trains the same network
against an equal mixture of Big Money, the draw-and-money teacher, a board-derived
engine, and frozen earlier policies. Four recent policy snapshots are retained;
the named baselines remain in the opponent pool. This is a simple league, not
the repository's evolutionary adversarial-league optimizer.

Observations expose the player's own hand and aggregate owned-card composition,
never its draw order. For this card pool all gains and trashing are known to the
owner. Opponent information is limited to hand, deck and discard sizes and turn
counts; hidden card identities are excluded. Public opponent purchase history
and inferred opponent deck composition are not yet encoded. This limits the
agent's ability to respond to the opponent's plan.

## Evaluation contract

The default deterministic split contains 64 training kingdoms, 8 validation
kingdoms, and 12 test kingdoms, drawn without replacement from the 3,003 possible
ten-card subsets. All three sets are stored in the checkpoint and checked for
duplicates and overlap. Card identities can occur in every split; the unseen
objects are complete kingdom combinations.

Only validation games select `best.pt`. The initial imitation policy is eligible,
so unsuccessful reinforcement learning cannot silently replace a better starting
model. `latest.pt` retains the most recent PPO policy and optimizer. The final
test command is a separate operation and never updates the model. The default
small validation sample is noisy; use more pairs for serious model selection.

Evaluation uses greedy legal choices, fresh opponents, and paired starting seats
with the same simulator seed. The same seed does not imply identical shuffles
after different policies make different decisions. Each baseline is reported
separately:

- `big_money`: the repository's existing Big Money factory, including its Copper
  fallback. Beating it alone is a weak bar.
- `draw_money`: the same board-aware teacher used during imitation. Results
  against this opponent do not establish independence from the teacher.
- `engine`: the first board-derived engine seed from `build_engine_seeds`; a
  kingdom without an eligible engine falls back to the draw-and-money teacher.
  These are reproducible archetype baselines, not every hand-tuned specialist
  in the strategy catalog.

Scores are wins plus half of ties divided by all scheduled games. Normal games
use victory points and then fewer turns taken as the tiebreak. A game that hits
the turn cap is reported separately and earns no evaluation credit; it is never
counted as a win or tie. Both the requested limit and the engine's 100-turn
safety cap are detected; a natural ending on the same boundary takes priority.
During PPO a capped episode emits zero reward but bootstraps its value target
from the final observation before reset. Advantage propagation stops at every
episode boundary, and only natural termination suppresses value bootstrapping.
Engine exceptions propagate as errors instead of silently becoming results.

JSON reports include individual games, seeds, seats, scores, turn caps, the
checkpoint SHA-256, and training metadata. Intervals resample whole kingdoms,
keeping dependent games together. With only twelve test kingdoms these intervals
are rough descriptions of variation, not proof of broad expert strength. Do not
repeatedly tune on the test results; reserve new kingdoms before the next cycle.

## Use a checkpoint in the simulator

```python
import torch
from dominion.rl.general.policy import GeneralAI, load_checkpoint

torch.set_num_threads(1)
policy, metadata = load_checkpoint("checkpoints/general-dominion-run/best.pt")
ai = GeneralAI(policy)
kingdom = metadata["splits"]["test"][0]
# Pass ai alongside an opponent to GameState.initialize_game, using get_card
# to turn these ten kingdom names into Card instances.
```

`GeneralAI` implements the same AI interface as existing strategies and returns
the original legal card object, preserving simulator identity requirements.
Checkpoints include an observation-schema version and ordered vocabulary and
reject incompatible layouts rather than silently assigning new meanings to
trained weights.

## Validation and remaining work

```bash
python -m pytest tests/rl -q
python -m pytest -q
python -m ruff check . --select E9,F63,F7,F82
python scripts/check_catalog.py
```

Tests cover hidden-hand and draw-order invariance, split disjointness, fixed
observation shapes across kingdoms and seats, legal card identity, checkpoint
compatibility, frozen league peers, real imitation/PPO updates, engine error
propagation, cancellation, scoring tiebreaks, and seat-paired evaluation.

The next strength milestones are independent training seeds, a larger untouched
test set, comparisons against compatible hand-tuned specialists, opponent-history
features, and stronger teachers or better exploration of engine construction.
Additional cards need explicit decision coverage and tests before being added
to the supported pool. Search at decision time is not implemented.

## Recorded first training run

The first run used seed 42, 800 teacher games (106,637 recorded decisions),
15 imitation epochs, and 100 PPO iterations of 2,048 decisions each. It took
approximately 10.4 minutes on this machine, excluding the final evaluations.
The network has 37,491 parameters.

Final selection compared the saved imitation model, the checkpoint retained
during training, and the last checkpoint using five seat pairs per validation
kingdom. The model from PPO iteration 60 won that comparison. Its validation
scores were 84.4% against Big Money, 47.5% against the draw-and-money teacher,
and 83.1% against the generated engine baseline. All final selection and test
matches disable the simulator's losing-purchase filter. The checkpoint retains
both the original training-source fingerprint and the final selection's source
fingerprint; the evaluation report separately identifies its running sources.

The usable local artifact is
`checkpoints/general-dominion-v1/validated.pt`. It is intentionally outside Git,
like other model checkpoints. Re-evaluate it with:

```bash
python -m dominion.rl.general.evaluate \
  checkpoints/general-dominion-v1/validated.pt \
  --split test --pairs 20 \
  --output .context/general-dominion-evaluation.json
```

The reinforcement learning test suite passes all 78 tests. The full repository
run passed 3,061 tests and failed
`TestCustomConditionSignatures::test_copy_and_worker_roundtrip_preserve_signature`.
The same failure reproduced in an unchanged checkout (3,033 tests passed), while
all 31 tests in that file pass independently. This existing serialization/test-order
issue was left outside the general-agent change. The suite covers the review fixes for mandatory trash menus, the engine turn
cap, and value bootstrapping without leakage between episodes. Ruff's required checks and catalog validation pass.

The final [held-out benchmark](../scripts/data/general_dominion_evaluation.json)
contains 1,440 games: twelve unseen kingdoms, twenty seed pairs per kingdom,
and three opponents. No games reached the turn cap.

| Opponent | Wins | Ties | Losses | Match score | Kingdom bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing Big Money | 363 | 15 | 102 | 77.2% | 64.5–87.5% |
| Draw-and-money teacher | 209 | 21 | 250 | 45.7% | 39.5–52.8% |
| Generated engine baseline | 333 | 7 | 140 | 70.1% | 51.9–86.4% |

Each row has 480 games. Match score counts a tie as half a win. These results
support a useful first player on new combinations within the supported pool:
it beats the weaker baselines in aggregate and competes with the teacher, but
does not establish superiority to that teacher, hand-tuned specialists, or
strong human players. This is one training seed; variation between independent
training runs has not been measured. The test kingdoms have now been evaluated
and should not guide further model tuning.

After the review fixes, replaying the same checkpoint reproduced every one of
the 1,440 game outcomes and all aggregate scores exactly; the checked-in report
records the updated evaluation-source fingerprint.
