# Shared card decisions and optimization backlog

Strategies should inherit useful card tactics and override only the decisions
that differ for their plan. A simulated loss should not silently reflect a
missing decision hook or an arbitrary supply ordering.

## How to track the work

Use the parent issue, [Improve shared card decisions and strategy overrides
(#344)](https://github.com/jss367/py-overlord/issues/344),
with this inventory as its checklist. Create child issues by decision family,
and use expansion names as coverage labels. Cross-expansion work often shares
the same selection and forwarding code.

Create an individual card issue when it has a distinct rules bug, a complex
policy, or a reproducible tactical failure. Avoid opening an issue for every
card before auditing it: many cards have no internal choice, and one shared
fix can improve several cards. Fixed-effect cards can still need action-order
evaluation, which belongs to the shared sequencing work.

Suggested child issue titles, in priority order:

1. **Make supply action selection reusable across strategies** — Overlord,
   Captain, and Band of Misfits; separate supply targets from hand play order.
2. **Make free gains and stored-card decisions strategy-aware** —
   Quartermaster, Workshop, Remodel, and Anvil; distinguish free gains from
   purchases and verify collection timing.
3. **Share trashing, discard, and set-aside decisions** — Chapel, Junk Dealer,
   Gear, Haven, and Anvil's discard decision; preserve useful cards according
   to the hand and deck, with strategy exceptions.
4. **Expose reaction and duration timing decisions to strategies** — Barge,
   Sleigh, and Torturer; connect missing overrides and evaluate timing.
5. **Measure tactical defaults and expand the card inventory** — reproducible
   decision scenarios, seeded comparisons, and an audit of remaining expansions.

The parent tracking issue is open. These decision families are tracked in
[#390](https://github.com/jss367/py-overlord/issues/390),
[#391](https://github.com/jss367/py-overlord/issues/391),
[#392](https://github.com/jss367/py-overlord/issues/392),
[#393](https://github.com/jss367/py-overlord/issues/393), and
[#394](https://github.com/jss367/py-overlord/issues/394), respectively.

## Status vocabulary

- **Needs forwarding:** a choice exists on the AI or in the engine, but a normal
  strategy cannot override all of it through `GeneticAI`.
- **Needs context:** a generic priority list is available, but distinct decisions
  share that list or lack a fallback suited to the card effect.
- **Connected and tested:** a shared baseline and strategy override are exercised
  through the engine. This does not mean the baseline plays optimally.
- **Evaluated:** targeted decision scenarios and seeded comparisons have measured
  the policy; record the evidence and limitations before using this status.
- **Unreviewed:** no claim about either correctness or tactical quality.

## Initial inventory

This is a prioritized source inspection, not a complete audit of every card.
All unlisted cards remain unreviewed. Prioritize cards on the kingdoms being
tested, then expand coverage by expansion.

| Card | Expansion | Decision | Current status and next work |
| --- | --- | --- | --- |
| Overlord | Empires | Select a supply Action | Connected and tested; targeted scenarios and seeded supply-policy comparisons measured attacks, trashing, and action support. Duration valuation has scenario coverage only; indirect-play and proxy ownership rules remain in #396 and #397. |
| Courier | Allies | Select an Action or Treasure from discard | Connected and tested: discard reactions resolve before selection; supports strategy overrides and declining. Default considers Courier chains, needed Actions, printed draw, and money. Strength comparisons remain unevaluated. |
| Quartermaster | Plunder | Select a gain and collection timing | Evaluated on a fixed-seed panel; hand-aware one-card collection, endgame points, independent piles, repeated plays sharing a pile, and start-of-turn scheduling are covered. Improvements vary by opponent; see the free-gain evaluation below. |
| Captain | Promo | Select a supply Action | Connected and tested; independent supply priorities and shared mandatory fallback. Seeded comparisons measured improvements on the tested board. Next-turn scheduling/replay rules remain in #395. |
| Band of Misfits | Dark Ages | Select a supply Action | Connected and tested; dedicated strategy forwarding and independent supply priorities. Seeded comparisons found smaller, uncertain gains. Indirect-play and proxy ownership rules remain in #396 and #397. |
| Workshop | Base | Select a free gain | Evaluated; separate free-gain context and priorities, ownership-aware mandatory fallback. Generic independent priorities regressed against some opponents; opt in and tune per strategy. |
| Remodel | Base | Choose a trash/gain pair | Evaluated; compare legal trash/gain pairs, honor explicit trash preferences, and refresh gains after trash reactions. The panel improved against some opponents; no optimality claim. |
| Anvil | Prosperity | Discard a Treasure, then gain | Evaluated; combined discard/gain override and shared tradeoff baseline. Both existing separate overrides remain authoritative. Panel results include small regressions and overlapping intervals. |
| Chapel | Base | Choose up to four trashes | Connected and tested: optional stopping, four-card cap, legal physical choices, conditional economy floors, and endgame preservation. Trash priorities remain strategy-owned. |
| Junk Dealer | Dark Ages | Choose a mandatory trash | Dedicated override was already forwarded. Invalid/declined choices now use the mandatory base fallback. Tests preserve useful economy when junk is available; no hard economy floor can prevent a mandatory trash. |
| Gear | Adventures | Choose cards to set aside | Connected, tested, and evaluated on a fixed kingdom: shared baseline saves stranded Actions or money above a buy breakpoint and can stop at zero. Multiple copies and replays conserve cards; no-choice plays leave at current cleanup. |
| Haven | Seaside | Choose a card to set aside | Connected, tested, and evaluated on a fixed kingdom: shares next-turn selection with Gear, then reuses the generic discard hook with reason `"haven"`. Mandatory legal fallback, per-copy replay storage, scoring and delayed returns are tested. |
| Barge | Menagerie | Resolve now or next turn | Needs forwarding; evaluate hand and action context. |
| Sleigh | Menagerie | Redirect a gained card | Needs forwarding; evaluate whether to spend the reaction. |
| Torturer | Intrigue | Respond to attack and choose discards | Response mode and generic discard selection are already forwarded (`reason="torturer"`); their policy evaluation belongs to #393. |
| Watchtower | Prosperity | Trash, topdeck, or keep a gain | Existing connected defaults and tests; evaluate exceptions by strategy and game stage. |
| Clerk | Prosperity | Reaction play and attack topdeck | Existing connected defaults and tests; evaluate exceptions. |
| Investment | Prosperity | Take money or trash a Treasure for points | Existing connected defaults and tests; evaluate point-versus-economy tradeoffs. |
| Bounty Hunter | Menagerie | Choose a card to exile | Existing strategy priority override and base fallback; evaluate reuse and exceptions. |
| Knights / Rogue | Dark Ages | Attacked player picks which revealed $3-$6 card to trash | Connected and tested (`choose_card_to_trash_for_knight_attack`, `choose_card_to_trash_for_rogue_attack`): against a Knight the default gives up a revealed Knight (which also trashes the attacker's), else the cheapest card; against Rogue it is simply the cheapest card. |
| Stables | Hinterlands | Discard a Treasure for +3 Cards +1 Action, or decline | Connected and tested (`choose_treasure_to_discard_for_stables`): default Copper, then Spoils, then Silver; strategies may decline. |
| Spice Merchant | Hinterlands | Optional Treasure trash and mode | Connected and tested (`choose_treasure_to_trash_for_spice_merchant`, `choose_spice_merchant_mode`): default only trashes Copper, draws unless the hand is short of money with no Actions left. |
| Armory | Dark Ages | Select a free $4 gain onto the deck | Connected and tested (`choose_armory_gain`): default runs the gain priorities over the exposed piles (the top Knight included). |
| Artificer | Adventures | Discard count and gain onto the deck | Connected and tested (`choose_artificer_gain`): default spends only junk (Curses, Victory cards, Coppers) and skips $0 gains; discards go through `choose_cards_to_discard` with reason `"artificer"`. |
| Scheme | Hinterlands | Action to topdeck at Clean-up | Connected and tested (`choose_card_to_topdeck_for_scheme`): default takes the most expensive discarded Action; Durations staying in play are excluded. |

Traceability: choice forwarding is in
[`GeneticAI`](../dominion/ai/genetic_ai.py); existing AI heuristics are in
[`AI`](../dominion/ai/base_ai.py); priority behavior and card overrides are in
[`EnhancedStrategy`](../dominion/strategy/enhanced_strategy.py). Quartermaster's
decisions are in [`GameState`](../dominion/game/game_state.py).

## First implementation: Overlord and Quartermaster

The shared functions in
[`tactical_defaults.py`](../dominion/ai/tactical_defaults.py) rank legal menus.
Both the base AI and normal strategies use them. Card effects construct and
validate menus; `GeneticAI` forwards the following strategy hooks:

| Strategy hook | Baseline behavior |
| --- | --- |
| `choose_overlord_target(state, player, choices)` | Retain existing action preferences, then the shared supply-play baseline described below. A dedicated method override can differ from hand order. |
| `choose_courier_target(state, player, choices)` | Try Action preferences, then explicit Treasure preferences. Otherwise chain Courier while a deck remains, supply needed Actions, then compare available printed draw and money. Returning `None` declines the optional play. |
| `choose_quartermaster_gain(state, player, choices)` | Use the contextual free-gain selector with Quartermaster storage as the declared destination. |
| `quartermaster_take_all(state, player, mat)` | Compatibility timing hook: collect one useful stored card promptly, prefer immediate Action support/draw/money, gain late points that already score on the mat, and avoid mandatory junk gains. |

For Overlord and Quartermaster, conditional rules that fail are deprioritized
in favor of unspecified cards.
When every candidate is covered by a failed rule, the baseline still chooses
from the legal menu. A card-selection override returning `None` or an unavailable
card requests the engine fallback. An empty menu produces no selection.
Collection returns a boolean and can explicitly keep accumulating with `False`.

Courier differs from those mandatory target fallbacks: `None` or an invalid
selection skips its optional play. Its menu contains physical cards currently
in the discard pile, after the top card has been discarded and all discard
reactions have resolved. Both Actions and Treasures use the engine's play
handling; Courier never trashes the top card. Strategies can override
`choose_courier_target` independently of hand play order. Failed conditional
Action or Treasure rules exclude those cards from Courier's default fallback,
including active phase Action rules; it may decline when none remain.

Courier's baseline avoids chaining when an empty deck would shuffle away the
other targets. It does not evaluate every card's special effects or guarantee
that a play is beneficial; use a conditional preference or a dedicated override
to decline unwanted plays. Rules, selection, and interaction coverage live in
[`test_courier.py`](../tests/test_courier.py). No seeded strength comparison has
been performed for this baseline.

For example, a strategy can define `choose_overlord_target` to select an attack
without moving that attack ahead of its Villages in normal hand play, or define
`choose_quartermaster_gain` to choose a different card from its purchase order.
Existing phase-specific priorities are consulted through the normal selectors.

The legal supply-play menus reject debt and Potion costs and apply current
coin-cost modifiers. All three Commands exclude Command targets; Captain also
excludes Durations. Only exposed, nonempty Supply piles are offered, including
the top Knight or Ruins and live Action types under Enlightenment. Newly legal
Enlightenment Treasure targets use the shared indirect Action handler, including
substitution, Ways and Action counters. Ordinary Action targets on Overlord and
Band of Misfits retain the separate #396 rules backlog. Buy-only restrictions
do not apply to plays.
Quartermaster gains still use the engine's gain/reaction path.

Storage per physical copy, cloned ownership, and gain reactions were covered
by #343. The subsequent rules audit for #391 adds repeated recurring choices
on the same pile and defers Quartermasters played during start-of-turn effects.
This is targeted rules coverage, not certification of every landscape or
special-card interaction.

The new hooks are available to Python strategies. They are not new genes in the
optimizer: existing priority lists can influence the baseline, but searching
dedicated policy parameters requires additional optimizer work.

## Free gains and stored cards: implementation and evaluation

[Make free gains and stored-card decisions strategy-aware (#391)](https://github.com/jss367/py-overlord/issues/391)
covers Workshop, Remodel, Anvil, and Quartermaster. The shared baseline lives in
[`tactical_defaults.py`](../dominion/ai/tactical_defaults.py); legal menus and
canonical selections live in [`gain_decisions.py`](../dominion/cards/gain_decisions.py).
Workshop no longer calls `choose_buy`. Purchases retain `choose_gain` for API
compatibility; free gains use `choose_free_gain(state, player, choices, context)`.

`FreeGainContext` records the source, declared destination (`discard`, `hand`,
`deck`, or `quartermaster` storage), a hand snapshot, owned counts including
stored/exiled cards, endgame status, any sacrificed card, and whether the gain
is mandatory. For a proposed Remodel pair, the snapshots exclude the proposed
trash. Reactions still resolve through `gain_card` and can change the final
destination. Endgame detection uses a present Province/Colony pile at two or
fewer cards, or two empty physical Supply piles via `state.empty_piles`; empty
members of a still-live split pile and tracked non-Supply piles do not advance
that horizon. It is intentionally approximate. Gain menus contain one exposed
option per physical pile via `supply_pile_key`/`top_supply_card`; validated gains
remove that exposed card with `take_top_supply_card`, while ownership and gain
selection remain keyed by the actual card name.

`free_gain_priority = None` inherits existing gain preferences, including active
phase rules. An explicit list separates free gains from purchases; `[]` uses
only the tactical fallback. Conditional preferences and ownership limits use
normal `PriorityRule` predicates. Failed conditions deprioritize covered cards;
when every rule fails, a mandatory gain still picks a legal card, while Anvil's
optional exchange may decline. A dedicated contextual override can use all
context fields, including destinations, to specify a different policy.

Anvil's optional decision is whether to discard the Treasure. Once it is
discarded, the gain is mandatory if a legal card remains, as clarified by the
[official FAQ reproduced on the Anvil page](https://wiki.dominionstrategy.com/index.php/Anvil#Official_FAQ).
A Friendly discard can consume the selected pile's last card before Anvil's
gain resolves. The engine then rebuilds the legal menu and makes the committed
gain, even when only a Curse remains or the replacement strategy hook returns
`None`. If every legal pile is empty, no card is gained. Declining the initial
exchange leaves the Treasure in hand and triggers no discard reaction.

Direct AI adapters inherit their existing `choose_buy` selector for free gains
on the effect's legal menu: RandomAI remains random, RLAI requests a queued
decision, and GeneralAI uses its learned selector. This calls only the selector;
no purchase occurs, and neither coins nor buys filter or pay for the gain.
Empty menus request no decision. Mandatory effects validate the response and
fall back to a legal gain if the selector declines or returns an invalid card.
GeneticAI instead honors the strategy's contextual free-gain hook and separate
preferences. Teacher selectors propose choices without recording free gains or
joint Remodel pairs. The validated executor snapshots the final legal gain
menu and pre-gain observation after trash/discard reactions, and commits only
a successful matching gain. Workshop, Remodel, Anvil and Quartermaster all use
this contract. Remodel snapshots its physical trash before execution and commits
it after trashing succeeds; a Fortress returning to hand still counts as trashed.
Legacy trash selection during pair planning cannot duplicate that example.
Empty menus, failed gains and Trader replacement produce no phantom gain label.
Watchtower topdeck/trash still count as successful gains. Quartermaster taking a
stored card produces no gain example. No checkpoint decision vocabulary changes.

```python
strategy.free_gain_priority = [
    PriorityRule("Village", PriorityRule.max_in_deck("Village", 3)),
    PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 2)),
    PriorityRule("Silver"),
]
```

The default ranks printed draw and money, needed village support, diminishing
Action copies, junk, and late points. It is a modest heuristic: attacks,
landmarks such as Fountain, special gain effects, and engines may need a
strategy override. Do not replace a tuned strategy's gain list indiscriminately.

| Hook | Contract and baseline |
| --- | --- |
| `choose_free_gain(state, player, choices, context)` | Return a legal gain; Workshop/Remodel use a mandatory legal fallback for an absent or invalid selection. |
| `choose_remodel_option(state, player, options)` | Each option is `(physical_trash, legal_gains)`; return `(trash, gain)`. Baseline compares gain value against retained-card value, or honors explicit trash preferences. Invalid pairs use the baseline. The engine checks the trashed card’s current cost and rebuilds the gain menu after trash reactions. |
| `choose_anvil_option(state, player, treasures, choices)` | Return `(physical_discard, gain)` or `(None, None)` to decline. Default considers gain value versus lost Treasure income; invalid pairs decline. Existing gain/discard overrides remain authoritative, including explicitly spending a Gold. |
| `choose_quartermaster_option(state, player, mat, candidates)` | Combined gain/take override for one recurring instruction. Compatibility gain/timing hooks still work. Collection selects one card by current-hand usefulness. Each replay sees the preceding choice's updates; different physical copies see only their own storage. |

The 54 targeted regression scenarios in
[`test_free_gain_tactics.py`](../tests/test_free_gain_tactics.py), plus existing
shared, Plunder, and adapter tests, separate policy choices from rules checks.
Distinct rules defects are tracked as [Workshop cost limits (#399)](https://github.com/jss367/py-overlord/issues/399),
[Remodel replacement costs (#400)](https://github.com/jss367/py-overlord/issues/400),
and [Quartermaster recurring instructions (#401)](https://github.com/jss367/py-overlord/issues/401).
The audit uses the official [Alchemy](https://www.riograndegames.com/wp-content/uploads/2013/02/DomAlchemy.pdf),
[Empires](https://www.riograndegames.com/wp-content/uploads/2022/03/Dominion-Rules-Empires.pdf),
[Menagerie](https://www.riograndegames.com/wp-content/uploads/2020/01/DominionMenagerie.pdf),
and [Plunder](https://www.riograndegames.com/wp-content/uploads/2022/08/DomPlunder.pdf) rules.

Reproduction:

```sh
PYTHONPATH=. python scripts/evaluate_free_gain_tactics.py --pairs 100 --seed 391000 --workers 4 --output .context/free_gain_tactics_reproduction.json
PYTHONPATH=. python scripts/render_free_gain_tactics_guide.py --results .context/free_gain_tactics_reproduction.json --output .context/free_gain_tactics_reproduction.html
```

The evaluator refuses existing output paths before starting games and creates
the output exclusively. If the local reproduction output already exists,
choose a fresh filename. These commands preserve all committed raw outcomes
and render a separate HTML copy from the newly produced data.

The dated [October 8 committed-action recording rerun](../scripts/data/free_gain_tactics_evaluation-2026-10-08-committed-recording.json)
uses the merged reviewed simulation inputs and covers 13,200 games: 100 seeds × two seats × two policies × 33 comparisons.
Controls reproduce the previous decisions using the same corrected rules;
opponents use current policies. Four representative kingdoms compare inherited
purchase preferences and opt-in independent fallback against Big Money, Smithy
money, and a Village/Smithy/Laboratory engine. Three existing Port Moresby
strategies are reevaluated against three board-specific opponents. Rate intervals
use an approximate Wilson bound on independent seed-pair means; change intervals
use paired normal estimates. These are unadjusted exploratory comparisons.
The [original raw outcomes](../scripts/data/free_gain_tactics_evaluation.json)
remain unchanged as historical evidence: their fingerprint matches the original
PR tree `4fc860b5`, while the distinct rerun fingerprint describes the fixed tree.
Nine comparison records changed in the first rerun. That
[first October 8 rerun](../scripts/data/free_gain_tactics_evaluation-2026-10-08.json)
is also retained unchanged. Export-only fixes subsequently changed the broad
source fingerprint; the [export-round-trip rerun](../scripts/data/free_gain_tactics_evaluation-2026-10-08-exports.json)
is retained unchanged as well. The [adapter-compatibility rerun](../scripts/data/free_gain_tactics_evaluation-2026-10-08-adapters.json)
is also retained. The recording/discovery rerun identifies sources after
final-gain teacher recording and reusable-strategy reference collection, plus
the evaluator's output-preservation guard. The
[recording/discovery rerun](../scripts/data/free_gain_tactics_evaluation-2026-10-08-recording.json)
is also preserved; the final audit rerun identifies the nullable policy's
identity, crossover, normalization/pruning and publication consumers. That
[policy-propagation audit rerun](../scripts/data/free_gain_tactics_evaluation-2026-10-08-policy-audit.json)
is preserved unchanged. The current rerun identifies the committed-action
recording contract; all 33 fixed-policy comparison records match the prior panel.
The panel uses GeneticAI strategies rather than learned/random adapters; its
results do not measure learned-policy or random-agent performance. The guide is generated from the final
rerun data, not relabeled historical results. Python exports and worker serialization preserve `free_gain_priority` as `None`,
`[]`, or explicit rules, and preserve Captain/Band target lists. Optimal exports
use the shared Python serializer while retaining their existing factory name.
Dynamic boards now also discover
cards referenced only in `free_gain_priority`; explicit boards remain authoritative.
Reusable-strategy discovery includes the same field when scoring references,
missing targets and seed overlap, including rules used only for free gains.

Findings, every comparison, uncertainty, regressions, and reproduction details
are published in the [Free Gains and Quartermaster Tactical Policy Evaluation](../reports/strategies/free-gains-and-quartermaster-policy-evaluation.html).
The study evaluates these fixed-policy panels only; it does not measure genetic
search improvements. No new free-gain mutation vocabulary was added. Saved catalog standings are preserved and marked outdated after
the simulation changes.

### Free-gain field propagation audit

`None` inherits purchases, `[]` requests tactical fallback, and ordered rules
specify a separate policy. Generic consumers preserve those distinct values.

| Consumer | Treatment |
| --- | --- |
| League, trainer confirmation and hall of fame | Shared `genome_signature` includes nullable ordered rules and structural condition fingerprints; same-card rules with different predicates remain distinct. |
| Baseline panel assembly | Deduplicates by original name and full rule signature; distinct policies receive unique labels on copies, including repeated merges. Name/spec-only island rosters identify registered factories rather than stored policy variants. |
| Deepcopy, selection, champions and worker transport | Whole strategies retain the nullable field. Python/optimal/island exports use the shared serializer; worker transport uses cloudpickle. |
| Positional and typed crossover | Can inherit either parent's complete setting, including resetting explicit rules to `None` or `[]`, without aliasing either parent. Both-inherited policies consume no extra random draw. |
| Mutation and typed promotion/recompilation | Purchase-module mutations preserve the configured side policy. Typed metadata owns purchase/action/trash modules, not the free-gain list, and recompilation preserves it on the copied strategy. Fresh random genomes start with inheritance. |
| Syntactic cleanup and normalization | Simplify non-null lists while retaining `None` and `[]`; publication recognizes free-gain-only Action references and lint includes the list. |
| Empirical pruning and parallel rule fires | Reset, collect, return and merge free-gain fire indices; prune explicit rules with the existing minimum-rule floor. Inheritance remains `None`. |
| Discovery and evidence summaries | Dynamic kingdoms and reusable-seed overlap include free-gain references. League JSON summaries retain null versus empty versus explicit rules. |

Cross-path regressions exercise all modes and distinct same-card conditions,
identity/deduplication, both crossover APIs, promotion/mutation/normalization,
clone and export round trips, publication cleanup, and real serial/parallel
free-gain fire reporting. Approximate buy-menu similarity remains a diversity
heuristic, separate from exact policy identity; this audit adds no training run.

## Supply Action selection: implementation and evaluation

Issue [#390](https://github.com/jss367/py-overlord/issues/390) connects Captain
and Band of Misfits through the card → `GeneticAI` → strategy path. They use
`captain_target_priority` and `band_of_misfits_target_priority`, respectively:
ordered `PriorityRule` lists with the usual `(state, player)` conditions.
Neither consults hand `action_priority` or active phase hand rules. Payloads
referenced only in these lists are included in automatically inferred kingdoms
and catalog/card-usage metadata. Strategies
can instead override `choose_captain_target(state, player, choices)` or
`choose_band_of_misfits_target(state, player, choices)`. Overlord retains its
existing action/phase preferences and independent method override for backward
compatibility.

For both new priority lists, failed conditions prefer unspecified targets.
If all conditions fail, or an override returns `None`, an unavailable card, or
an invalid object, the card selects from its legal menu using the shared
baseline. All three supply plays are mandatory when legal targets exist;
`None` cannot decline them. No hook is called for an empty menu. Captain makes
a fresh decision on its next-turn resolution using the current hand and costs.
Choices never consume Supply copies. Older strategies lacking the new methods
receive the base AI's shared fallback; Captain does not call their hand selector.

`choose_supply_action_target(state, player, choices)` prioritizes Action
support when current terminal Actions outnumber remaining Actions. It then
compares available draw (capped by deck plus discard), money, attacks, junk
trashing and discounted future resources. Militia pressure uses opposing hand
sizes; Witch, Sea Hag and Familiar receive no cursing premium when Curses are
exhausted. Chapel, Steward and Junk Dealer have bounded trashing estimates;
Copper is only fuel with at least $3 of other printed Treasure economy, and
small Victory cards stop being junk with two Provinces left. Mandatory Junk
Dealer trash is penalized in a clean hand. Caravan, Fishing Village, Wharf,
Merchant Ship and Lighthouse have explicit immediate/future estimates; future
value is discounted by 25% and dropped with two Provinces left. Pillage is
penalized because its virtual self-trash cannot pay out. Feast is not penalized:
its gain is unconditional, even when it cannot trash itself. Unknown
effects use printed resources and a coarse Attack premium. Ties use Actions,
Buys, printed coin cost, then name. These are modest heuristics, not optimal play.

[Published supply Action evaluation](../reports/strategies/supply-action-selection-evaluation.html)
records targeted scenarios, exact purchases, nine opponent comparisons,
3,600 games with fixed seeds and both seats, conservative uncertainty bounds,
and limitations. Raw evidence is
[`supply_action_evaluation.json`](../scripts/data/supply_action_evaluation.json);
reproduce with:

```bash
PYTHONPATH=. python scripts/evaluate_supply_actions.py --pairs 100 --seed 39000 \
  --output .context/supply-action-reproduction.json
```

This is evaluation of target policies in the current simulator, not full card
certification. The rules audit found and separately filed:

- [#395: Captain scheduling and repeated plays](https://github.com/jss367/py-overlord/issues/395).
- [#396: Overlord and Band of Misfits indirect Action handling](https://github.com/jss367/py-overlord/issues/396).
- [#397: Virtual Supply proxies and Duration owner tracking](https://github.com/jss367/py-overlord/issues/397).
- [#405: Pillage self-trash condition and payoff ordering](https://github.com/jss367/py-overlord/issues/405).

Strict expected-failure tests reproduce these defects in
`tests/test_shared_card_tactics.py`. Matches exclude Duration payloads; Duration
valuation has scenario coverage only. Captain matches retain the current
scheduling defect for both policies, so their absolute strength is provisional.
The target estimate does not inspect every nested decision, every defense, or
an opponent's full deck, or value resource substitutions under Enlightenment;
dedicated overrides remain appropriate. The optimizer
has no new genes for the dedicated lists.

No currently registered strategy references these three Commands. The synthetic
Command purchase policies were reevaluated against the registered Smithy money,
Village/Laboratory engine, and Chapel/Witch opponents. Catalog regeneration
preserves historical standings and marks them outdated; this comparison does
not replace the global tournament.

## Completion criteria for each implementation issue

- List the cards and decisions covered, with rules correctness tracked separately
  from tactical quality.
- Use one reusable baseline with a working strategy override for each decision.
- Test the real engine-to-AI-to-strategy path, conditional preferences, empty
  menus, invalid choices, and relevant gain/reaction interactions.
- Test representative tactical situations: early building, a constrained hand,
  excessive copies, and endgame decisions where relevant.
- Record comparisons under fixed seeds and representative opponents before
  labeling a policy evaluated. Report uncertainty and regressions, not just a
  winning example. Reevaluate affected strategies when defaults change.
- Update the inventory with remaining limitations. Hook coverage alone is not
  proof of good play.

First-implementation regression tests:
[`test_shared_card_tactics.py`](../tests/test_shared_card_tactics.py), with
existing interaction coverage in
[`test_plunder_kingdom_cards.py`](../tests/test_plunder_kingdom_cards.py) and
[`test_genetic_ai_hooks.py`](../tests/test_genetic_ai_hooks.py).

## Trashing, discard, and next-turn storage evaluation

Issue [#392](https://github.com/jss367/py-overlord/issues/392) adds Gear and Haven
forwarding through `GeneticAI`. Both use
`tactical_defaults.choose_next_turn_cards(state, player, choices, count)`.
Gear may return zero to two cards. Haven first considers one useful next-turn
card, then calls the existing generic discard selector with `reason="haven"`.
A dedicated Haven override returning `None` does not waive its mandatory
selection: the card effect picks a legal fallback. Invalid Gear choices are
ignored; invalid Chapel choices stop optional trashing; invalid Junk Dealer
choices trigger its existing mandatory trash baseline. Anvil may decline its
discard and must select an actual Treasure from the legal hand menu.

The shared discard ranking now puts all pure Victory cards and Curses before
live cards, then Copper and cheaper cards. It preserves Action/Victory,
Treasure/Victory, and Night cards as live choices. Strategy discard overrides
remain authoritative. Chapel continues to use existing strategy trash
priorities, including conditional rules for stopping at a minimum economy or
preserving late points. Junk Dealer and Anvil keep their existing trash/discard
policies: the former must sacrifice something even in a hand of useful cards;
the latter's preference for discarding the cheapest Treasure does not evaluate
its gain jointly.

The storage baseline reserves printed supply-cost breakpoints (with current
cost reductions), including a $3 building floor when available. It accounts
for remaining Actions, Villagers and printed action support before or during
the Action phase when identifying stranded Actions. After that phase these
resources cannot make an Action playable. Hand Treasure income contributes only
before or during the Treasure phase; storing one removes its entire projected
income, including known external bonuses. Later indirect plays through Toil or
March do not reopen earlier phases, so newly drawn money can be saved without
preserving fictitious buy breakpoints. Ordinary play budgets apply only on the
owner's turn. Hybrids remain in hand while their Treasure or Night play phase is
still available. The baseline avoids saving pure
junk under optional Gear, and preserves this turn when the final Province/Colony
can legally be bought during a remaining Buy phase with an unspent Buy.
Coin tokens (Coffers) are spendable currency alongside coins. The engine's
read-only affordability helper supplies legal coin-only Supply breakpoints,
including effective costs, Debt, banned buys and Mission restrictions.
It does not model
special card text, draw order, landscapes, multiple purchases or three-pile
endings. The baseline also projects known pending pile-token, Champion,
Prophecy and Ally resource bonuses. Scoped play context identifies the actual
played card, including Way proxies and unresolved enclosing plays; forecasts
never apply bonuses early. Harbor Village uses the current caller's existing
bonus timing. Future Action support includes these known external Action bonuses
as well as printed Actions. Pending draws, optional reactions and extra buys are
not forecast. A strategy can override either dedicated storage decision.

Resource audit for this baseline:

| Resource | Projection boundary / engine source |
| --- | --- |
| Coins and Coin tokens/Coffers | Current balances plus known pending coin bonuses and hand Treasure income; `_get_affordable_cards` uses their combined spendable total and `_commit_buy` spends coins then tokens. Existing negative-coin penalties are already in the coin balance. |
| Hand Treasure income | Printed coins plus known external coin bonuses, only on the owner's turn before/during Treasure phase; the same contribution is removed when storing that physical card. Live Treasure type includes Capitalism; special text and conditional Treasure/replay effects are not interpreted. |
| Pending play resources | Pile tokens, Champion, the supported Prophecy/Ally bonuses and Harbor Village, scoped to the real played card and the caller's unresolved hooks; bonuses already awarded are not counted twice. |
| Actions and Villagers | Current balances and known pending Actions only before/during Action phase, plus printed/known external net Action support from hand. Printed Action bonuses respect `ignore_action_bonuses`; late or off-turn Actions cannot reopen a phase. Optional Reserve calls, special play permissions and play-limit landscapes are not forecast. |
| Buys | A remaining current Buy is required for final-pile suppression; future extra Buys and multiple purchases are not projected. |
| Potions, Debt and legality | Live engine restrictions are retained. The policy only reserves zero-Potion, zero-Debt Supply prices, uses `get_card_cost` for discounts, and does not forecast Potion income or discretionary Debt payments. |
| Other counters | Favors only inform the supported Ally resource bonus; VP, Sun, Pirate Ship and other effect-specific counters are not spendable purchase currency and are not added to cash. |


Card-conservation and retention corrections are separately tracked in
[#398 — Fix lost set-aside cards when Gear or Haven is replayed](https://github.com/jss367/py-overlord/issues/398).
Storage accumulates per physical copy across plays; all stored cards return
once next turn. Haven's list-valued storage is included in ownership/scoring.
A play without storage schedules no Duration instruction; an empty later replay
preserves earlier storage. Tests also cover completed Duration cleanup and
Throne Room replaying two successful storage effects. Multiplier retention
when only one replay schedules a future effect remains a broader engine audit;
this change does not certify every multiplier/Way/Command combination.

The [published comparison](../reports/strategies/trashing-discard-and-next-turn-card-decisions.html)
contains complete results, uncertainty, score-margin regressions, policies,
seeds and reproduction commands. Both comparison arms use the corrected card
rules, isolating the policy change. Registered Big Money and Chapel Witch are
reevaluated alongside four diagnostic decks and three representative opponents.
Saved catalog standings are retained and marked outdated by catalog
regeneration; this focused study does not replace a full tournament.

Coverage: [`test_set_aside_tactics.py`](../tests/test_set_aside_tactics.py),
existing expansion tests, and
[`evaluate_set_aside_tactics.py`](../scripts/evaluate_set_aside_tactics.py).
