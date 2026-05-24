# Endgame Guard via Real-Buy Simulation — Design

**Date:** 2026-05-19
**Status:** Implemented
**Successor to:** PR #275 — merged as `cd76f7e Veto buys that would end the game while losing` (enumeration-based interim guard)
**Branch:** `start-philadelphia-claude` (workspace `minnetonka-v2`)

---

## Problem

This design replaced the PR #275 version of `GameState.gain_would_lose_game`,
which *modeled* what a buy
does (`supply -= 1; player.discard.append(card)`) instead of performing it.
The real buy path applies VP-token hooks (Goons, Groundskeeper, Collection,
all VP-awarding Landmarks) and supply-restoring reactions (Exile reclamation,
Trader, Changeling), plus various on-buy / on-gain effects. Every omission is
a divergence between the model and reality:

- **False vetoes** — the model under-counts buyer VP or over-counts pile
  depletion, so the guard refuses a buy that would actually win or wouldn't
  end the game. Three review rounds on #275 found three distinct classes of
  these.
- **False negatives** — the model says "safe" while a side effect actually
  ends the game in a loss. No reviewer is guaranteed to catch these; the
  enumeration approach can't detect the failure direction at all.

The interim mitigation enumerated divergences and stood the guard down when
they were detected. That approach required exhaustive understanding of a
4 k-line engine and only covered one of the two failure directions, so it was
replaced by the real-buy simulation below.

## Principle

**Execute reality, don't model it.** Replace the hand-rolled simulation with:
deep-copy the game state, perform the *actual* buy on the copy, then check
end-condition and scores on the copy. There is no model, so there is nothing
to diverge. New cards, landmarks, or reactions are handled automatically.

## Architecture

```
choose_buy
    └── _choose_safe_buy(player, affordable)            (unchanged)
            └── gain_would_lose_game(player, card)      (rewritten)
                    1. _losing_pileout_allowed?           → False
                    2. _all_decision_hooks_pure?  no      → False
                    3. _buy_could_end_game?       no      → False
                    4. save random.getstate()
                    5. clone = copy.deepcopy(self)
                    6. clone._commit_buy(clone_player, clone_card)
                    7. end? compare VP; tie ⇒ would-lose
                    8. restore random.setstate()
```

### Gate: `_buy_could_end_game(player, card)`

A *loose necessary condition*, cheap and pure: returns True iff the game is
near ending at all — `Province ≤ 2`, or `Colony ≤ 2` (if in supply), or
`empty_piles ≥ 2`. May trigger unnecessary copies (harmless), but **never
skips a possible ending**, so it can't reintroduce the modelling bug in the
gate itself. Keeps deepcopies to a handful per game, even under the GA.

### Clone: `GameState.__deepcopy__(self, memo)`

Full deepcopy of the object graph (supply, players, landmarks/allies/projects
with their internal pools like `temple_pile_tokens`, `vp_pool` — all copied
correctly for free), with surgical exclusions:

- **AIs shared by reference** — preseed `memo[id(player.ai)] = player.ai` for
  every player. Don't copy strategies/networks.
- **Logger detached** — copy's `logger=None`, `log_callback=lambda *_: None`.
  No spurious logs/metrics; no file-handle issues.
- **Player back-reference fixed** — each cloned `player.game_state` re-points
  to the clone, not the original.

### Execute: `_commit_buy(player, card)`

Extract the per-card buy commit currently inlined in `handle_buy_phase`
(lines ~2042–2112: cost payment, `on_buy`, `gain_card`, landmark/ally/project
on_buy hooks, `_handle_on_buy_in_play_effects`,
`_apply_adventures_attack_on_buy`, overpay) into a method called by **both**
the real phase and the guard's clone. Single source of truth. Same code path
in both contexts.

### Evaluate

After `clone._commit_buy(...)`, use `_normal_game_end_reached()` on the clone.
This is authoritative because it reads the clone's *actual post-buy supply* —
all side effects (VP hooks, Trader/Changeling/Exile, extra gains) have already
been applied to the clone for real. Cannot use `is_game_over()` directly: it
returns `False` mid-turn by design.

If ended, compare `clone_player.get_victory_points(clone)` vs the best
opponent on the clone. Tie ⇒ "would lose" (preserved from PR #275; the engine
breaks ties by seat order via `max`, which a strategy must not bank on).

### Boundary: `_all_decision_hooks_pure(self)`

Returns True iff every `player.ai` has
`getattr(ai, "decision_hooks_are_pure", True) is True`. `RLAI` sets this to
`False`; `GeneticAI` inherits the default `True`. If False, the guard cleanly
disables (no veto) — RL games behave exactly as pre-PR-#275. This is the
chosen scope boundary: ship for the games the guard actually targets,
without pulling RL internals into scope.

### RNG isolation

The engine uses the module-global `random`. The simulated buy can trigger
shuffles/draws inside `gain_card`. Save `random.getstate()` before the clone
+ commit and `random.setstate(...)` after, so the real game's RNG stream is
unperturbed and the guard is deterministic.

## What gets deleted

After verifying no other callers (grep before removal):

- `_has_unmodeled_vp_on_gain` (the VP-hook enumeration)
- `_buy_pile_restorable` (the supply-restoration enumeration)
- The Temple/Castles "v1 caveat" — gone, because the real `on_gain` now runs
  on the clone.

## What is preserved

- `_normal_game_end_reached` (still the right post-buy structural check)
- `_supply_pile_name`, `_losing_pileout_allowed`, `_choose_safe_buy`
- `allow_losing_pileout` opt-out
- Tie semantics (`my_vp <= opp_best` ⇒ would-lose)

## Edge cases & risks

- **Recursion.** `_commit_buy` commits exactly one buy; nested gains go
  through `gain_card`, not `handle_buy_phase` / `_choose_safe_buy`. No
  re-entry into the guard.
- **Multiple re-asks.** `_choose_safe_buy` may evaluate several candidates;
  each that passes the gate gets its own clone. Bounded by `affordable` size;
  rare overall.
- **AI purity assumption.** Genetic strategies' decision hooks are pure
  priority-rule queries — verified by inspection of `GeneticAI` /
  `EnhancedStrategy`. RL is opted out via the boundary flag.
- **Performance.** The gate keeps the expensive path off the hot loop except
  near game end. Acceptance bar (below) measures it concretely.

## Testing strategy (TDD)

**Existing 12 guard tests kept verbatim.** Now executed against the real
buy path; they become more authoritative, not weaker. `provinces()` helper
and `[get_card]*n` aliasing fix from PR #275 stay.

**New tests:**

1. **False negative regression.** A buy whose `on_gain` empties an extra
   pile (Border Village–shape) producing a 3-pile-out the old enumeration
   model would have waved through. Buyer behind. New code vetoes; this is
   the failure direction PR #275 could not catch.
2. **RL boundary.** Set `ai.decision_hooks_are_pure = False` on the buyer
   in a behind+last-Province scenario; assert the guard disables (no veto).
3. **RNG isolation.** Seed `random`, exercise a buy whose simulated commit
   triggers a shuffle (e.g. an exile-reclaim path that draws), assert
   `random.getstate()` is identical before and after `gain_would_lose_game`.
4. **Clone correctness.** `copy.deepcopy(state)` returns a clone where
   `clone.players[0].ai is state.players[0].ai` (shared) and mutating
   `clone.supply` does not affect `state.supply`.
5. **Temple/Castles.** Endgame buy of the last Temple/Castle produces the
   correct veto/non-veto outcome (prior v1 caveat is gone).

## Acceptance gate before merging the follow-up PR

- 12 existing + ~5 new tests green.
- Full non-slow suite green.
- Slow simulation suite wall-clock regression **< ~15 %**.
- One ad-hoc genetic-trainer timing run (N games, before/after) confirming
  copies stay rare. If exceeded → **tighten the gate, never weaken
  correctness.**
- Grep confirms `_has_unmodeled_vp_on_gain` / `_buy_pile_restorable` have
  zero remaining callers before deletion.

## Rollout

- **PR #275** merged as `cd76f7e` on `main` — the enumeration-based interim
  guard is now production code.
- **This branch** (`start-philadelphia-claude`, workspace `minnetonka-v2`)
  is the follow-up off updated `main`. Diff is a clean refactor of the
  interim: replace `gain_would_lose_game`'s body, delete the two enumeration
  helpers (`_has_unmodeled_vp_on_gain`, `_buy_pile_restorable`), keep the
  existing test contract, add the new tests below.
- Implementation done test-first; PR'd against `main`.

## Decisions log

The five validated design choices (questions in the brainstorm session):

1. **Correctness boundary.** Pure-AI only with explicit fallback. RL games
   skip the guard rather than pulling RL internals into scope.
2. **Gate.** Loose "game is near ending" check (`Province ≤ 2` /
   `Colony ≤ 2` / `empty_piles ≥ 2`). Not a precise predictor — a precise
   gate would reintroduce the modelling bug.
3. **Clone mechanism.** `__deepcopy__` with surgical exclusions (AIs shared,
   logger detached, back-ref fixed). Not field enumeration; not serialize.
4. **Execute "the real buy".** Extract `_commit_buy` from `handle_buy_phase`
   and call it on the clone. Single source of truth.
5. **Validation bar.** Tiered: correctness (existing + new tests, including
   false-negative and RL-boundary), no regressions, slow-suite < ~15 % +
   ad-hoc GA timing. Failure mode: tighten the gate.
