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
#390, #391, #392, #393, and #394, respectively.

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
| Overlord | Empires | Select a supply Action | Connected and tested; evaluate attacks, trashing, duration targets, and action support beyond printed resources. |
| Courier | Allies | Select an Action or Treasure from discard | Connected and tested: discard reactions resolve before selection; supports strategy overrides and declining. Default considers Courier chains, needed Actions, printed draw, and money. Strength comparisons remain unevaluated. |
| Quartermaster | Plunder | Select a gain and collection timing | Evaluated on a fixed-seed panel; hand-aware one-card collection, endgame points, independent piles, repeated plays sharing a pile, and start-of-turn scheduling are covered. Improvements vary by opponent; see the free-gain evaluation below. |
| Captain | Promo | Select a supply Action | Needs context: reuses hand action priorities and falls back to the first candidate. |
| Band of Misfits | Dark Ages | Select a supply Action | Needs forwarding: its dedicated base-AI hook is not forwarded to the strategy. |
| Workshop | Base | Select a free gain | Evaluated; separate free-gain context and priorities, ownership-aware mandatory fallback. Generic independent priorities regressed against some opponents; opt in and tune per strategy. |
| Remodel | Base | Choose a trash/gain pair | Evaluated; compare legal trash/gain pairs, honor explicit trash preferences, and refresh gains after trash reactions. The panel improved against some opponents; no optimality claim. |
| Anvil | Prosperity | Discard a Treasure, then gain | Evaluated; combined discard/gain override and shared tradeoff baseline. Both existing separate overrides remain authoritative. Panel results include small regressions and overlapping intervals. |
| Chapel | Base | Choose up to four trashes | Generic trash priorities are connected; evaluate stopping and minimum economy. |
| Junk Dealer | Dark Ages | Choose a mandatory trash | Dedicated trash hook is forwarded; evaluate keeping enough economy. |
| Gear | Adventures | Choose cards to set aside | Needs forwarding; evaluate current-turn versus next-turn value. |
| Haven | Seaside | Choose a card to set aside | Needs forwarding; evaluate next-hand usefulness. |
| Barge | Menagerie | Resolve now or next turn | Needs forwarding; evaluate hand and action context. |
| Sleigh | Menagerie | Redirect a gained card | Needs forwarding; evaluate whether to spend the reaction. |
| Torturer | Intrigue | Respond to attack and choose discards | Response mode and generic discards are forwarded; evaluate both policies. |
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
| `choose_overlord_target(state, player, choices)` | Try the strategy's action preferences. Otherwise prefer action support when terminal Actions exceed remaining Actions, then printed draw and money, with deterministic tie-breaking. |
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

The legal menus reject debt and Potion costs and apply current coin-cost
modifiers. Overlord also excludes Command cards, preventing self-selection.
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
fewer cards, or two empty piles; it is intentionally an approximate horizon.

`free_gain_priority = None` inherits existing gain preferences, including active
phase rules. An explicit list separates free gains from purchases; `[]` uses
only the tactical fallback. Conditional preferences and ownership limits use
normal `PriorityRule` predicates. Failed conditions deprioritize covered cards;
when every rule fails, a mandatory gain still picks a legal card, while Anvil's
optional exchange may decline. A dedicated contextual override can use all
context fields, including destinations, to specify a different policy.

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
PYTHONPATH=. python scripts/evaluate_free_gain_tactics.py --pairs 100 --seed 391000 --workers 4
```

The committed [raw outcomes](../scripts/data/free_gain_tactics_evaluation.json)
cover 13,200 games: 100 seeds × two seats × two policies × 33 comparisons.
Controls reproduce the previous decisions using the same corrected rules;
opponents use current policies. Four representative kingdoms compare inherited
purchase preferences and opt-in independent fallback against Big Money, Smithy
money, and a Village/Smithy/Laboratory engine. Three existing Port Moresby
strategies are reevaluated against three board-specific opponents. Rate intervals
use an approximate Wilson bound on independent seed-pair means; change intervals
use paired normal estimates. These are unadjusted exploratory comparisons.

Findings, every comparison, uncertainty, regressions, and reproduction details
are published in the [Free Gains and Quartermaster Tactical Policy Evaluation](../reports/strategies/free-gains-and-quartermaster-policy-evaluation.html).
The study evaluates these panels only; no dedicated policy genes were added to
the optimizer. Saved catalog standings are preserved and marked outdated after
the simulation changes.

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
