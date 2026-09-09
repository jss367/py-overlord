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

The parent tracking issue is open. The five child issue groups above are
proposed boundaries; separate child issues have not yet been opened.

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
| Quartermaster | Plunder | Select a gain and collection timing | Connected and tested; each copy keeps its own pile and collects one card per turn per the printed rules. Strategies may also override `choose_quartermaster_option` for a single hand-aware take/gain decision. |
| Captain | Promo | Select a supply Action | Needs context: reuses hand action priorities and falls back to the first candidate. |
| Band of Misfits | Dark Ages | Select a supply Action | Needs forwarding: its dedicated base-AI hook is not forwarded to the strategy. |
| Workshop | Base | Select a free gain | Needs context: calls the buy selector, which uses gain priorities; evaluate free-gain fallback and ownership limits. |
| Remodel | Base | Choose a trash/gain pair | Needs context: separate generic trash and gain choices do not evaluate the pair together. |
| Anvil | Prosperity | Discard a Treasure, then gain | Gain override is connected; Treasure-discard hook needs forwarding. |
| Chapel | Base | Choose up to four trashes | Generic trash priorities are connected; evaluate stopping and minimum economy. |
| Junk Dealer | Dark Ages | Choose a mandatory trash | Needs forwarding for its dedicated trash hook; evaluate keeping enough economy. |
| Gear | Adventures | Choose cards to set aside | Needs forwarding; evaluate current-turn versus next-turn value. |
| Haven | Seaside | Choose a card to set aside | Needs forwarding; evaluate next-hand usefulness. |
| Barge | Menagerie | Resolve now or next turn | Needs forwarding; evaluate hand and action context. |
| Sleigh | Menagerie | Redirect a gained card | Needs forwarding; evaluate whether to spend the reaction. |
| Torturer | Intrigue | Respond to attack and choose discards | Response mode is forwarded under `choose_torturer_response`; discard selection needs forwarding. |
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
| `choose_quartermaster_gain(state, player, choices)` | Try the strategy's gain preferences. Otherwise prefer non-junk, non-Victory gains, then printed cost and resources. |
| `quartermaster_take_all(state, player, mat)` | Decide whether this Quartermaster collects this turn (the card puts *one* stored card into hand; the engine takes the priciest). Baseline: collect when at least two cards are stored. |

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

The collection hook's name and behavior reflect the existing simulator. This
change does not certify the card's complete rules implementation. Storage per
physical card, duration-copy behavior, and full rules conformance need an
explicit audit before treating a strategy benchmark as authoritative.

The new hooks are available to Python strategies. They are not new genes in the
optimizer: existing priority lists can influence the baseline, but searching
dedicated policy parameters requires additional optimizer work.

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
