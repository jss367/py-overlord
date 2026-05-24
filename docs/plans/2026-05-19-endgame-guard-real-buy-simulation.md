# Endgame Guard — Real-Buy Simulation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `GameState.gain_would_lose_game`'s hand-rolled simulation (PR #275, merged `cd76f7e`) with a real-buy simulation: deep-copy the game state, run the actual buy on the copy via a shared `_commit_buy` method, evaluate the standard end-condition and scores on the post-buy clone. Eliminates the enumeration-and-stand-down whack-a-mole and the false-negative direction the prior approach could not catch.

**Status:** Implemented in `dominion/game/game_state.py`.

**Architecture:** A loose pre-check gate (game-is-near-ending) keeps `copy.deepcopy` off the hot path. `GameState.__deepcopy__` shares AIs by reference, detaches logger, fixes the player back-reference. `_commit_buy` is extracted from `handle_buy_phase` so the real game and the simulation execute the *same code*. RNG (module-global `random`) is saved/restored around the simulated buy. RL agents opt out via a `decision_hooks_are_pure = False` flag.

**Tech Stack:** Python (the existing `dominion` package), `copy.deepcopy` with `__deepcopy__` + `memo` preseed, `random.getstate/setstate`, pytest.

**Design doc:** `docs/plans/2026-05-19-endgame-guard-real-simulation-design.md` (commit `cf90c14`).

---

## Conventions used in this plan

- All paths are relative to the workspace root `~/conductor/workspaces/py-overlord/minnetonka-v2/`.
- Every task ends with a `git commit` so progress is recoverable mid-plan.
- `pytest` runs from the workspace root.
- TDD throughout: RED test first, run it, watch it fail; GREEN minimal impl; rerun to verify green; commit.

---

## Task 1: `GameState.__deepcopy__` — share AIs, detach logger, fix back-ref

**Files:**
- Modify: `dominion/game/game_state.py` (add `__deepcopy__` method on `GameState`; add `import copy` at top if not already imported).
- Test: `tests/test_endgame_purchase_guard_clone.py` (new file).

### Step 1 — write the failing test

Create `tests/test_endgame_purchase_guard_clone.py`:

```python
"""Cloning semantics required by the real-buy-simulation endgame guard.

The guard performs a real buy on a deep-copied GameState. The clone must:
* share each player's AI by reference (don't copy strategies/networks);
* drop the logger and replace log_callback with a no-op;
* re-point every player.game_state back-reference at the clone;
* be otherwise a fully independent copy (mutations don't leak back).
"""

import copy

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _make_two_player_state():
    p1 = PlayerState(DummyAI())
    p2 = PlayerState(DummyAI())
    state = GameState([p1, p2])
    state.log_callback = lambda *_: None
    state.supply = {"Province": 8, "Copper": 30}
    return state


def test_deepcopy_shares_ai_by_reference():
    state = _make_two_player_state()
    clone = copy.deepcopy(state)
    for original, copied in zip(state.players, clone.players):
        assert copied.ai is original.ai  # SAME object, not a copy


def test_deepcopy_detaches_logger_and_log_callback():
    state = _make_two_player_state()
    clone = copy.deepcopy(state)
    assert clone.logger is None
    # Calling the no-op must not raise and must not write anywhere.
    clone.log_callback("anything", "at", "all")


def test_deepcopy_fixes_player_game_state_backref():
    state = _make_two_player_state()
    # Establish the back-reference the engine sets up in real games.
    for p in state.players:
        p.game_state = state
    clone = copy.deepcopy(state)
    for cp in clone.players:
        assert cp.game_state is clone  # points at the CLONE, not the original


def test_deepcopy_supply_is_independent():
    state = _make_two_player_state()
    clone = copy.deepcopy(state)
    clone.supply["Province"] = 0
    assert state.supply["Province"] == 8  # original untouched


def test_deepcopy_player_zones_are_independent():
    state = _make_two_player_state()
    state.players[0].discard.append(get_card("Estate"))
    clone = copy.deepcopy(state)
    clone.players[0].discard.append(get_card("Duchy"))
    assert [c.name for c in state.players[0].discard] == ["Estate"]
```

### Step 2 — run the test, verify it fails

Run: `pytest tests/test_endgame_purchase_guard_clone.py -v`

Expected: most cases fail because there's no `__deepcopy__` override — the AI gets deep-copied (so `is` check fails), logger isn't detached, and back-ref points at the original.

### Step 3 — implement `GameState.__deepcopy__`

Add to `dominion/game/game_state.py` (near the top, ensure `import copy` is present; insert the method on `GameState`, e.g. immediately before `is_game_over`):

```python
def __deepcopy__(self, memo):
    """Deep-copy the game state with surgical exclusions.

    Used by the endgame-loss guard to evaluate a prospective buy by
    running the *real* buy on a copy of the state. The exclusions are:

    * Every player's ``ai`` is shared by reference (strategies/networks
      are not copied; their decision hooks are pure for the AIs the
      guard runs against — see ``_all_decision_hooks_pure``).
    * ``logger`` is detached (set to ``None``) and ``log_callback`` is
      replaced with a no-op so the simulated buy emits no spurious
      logs or metrics and we don't clone file handles.
    * The cloned ``player.game_state`` back-references are re-pointed
      at the clone automatically because ``memo[id(self)]`` is set
      before recursing.
    """
    cls = type(self)
    new = cls.__new__(cls)
    memo[id(self)] = new  # ensures player.game_state back-refs land on the clone
    for player in self.players:
        ai = getattr(player, "ai", None)
        if ai is not None:
            memo[id(ai)] = ai  # share AI by reference
    for key, value in self.__dict__.items():
        if key == "logger":
            new.logger = None
        elif key == "log_callback":
            new.log_callback = lambda *_: None
        else:
            new.__dict__[key] = copy.deepcopy(value, memo)
    return new
```

### Step 4 — run the test, verify it passes

Run: `pytest tests/test_endgame_purchase_guard_clone.py -v`

Expected: all five tests pass.

### Step 5 — commit

```bash
git add dominion/game/game_state.py tests/test_endgame_purchase_guard_clone.py
git commit -m "Add GameState.__deepcopy__ with shared AIs and detached logger"
```

---

## Task 2: `_buy_could_end_game` — the cheap gate

**Files:**
- Modify: `dominion/game/game_state.py` (add `_buy_could_end_game` method on `GameState`).
- Test: `tests/test_endgame_purchase_guard_gate.py` (new file).

### Step 1 — write the failing test

```python
"""The cheap pre-check that decides whether to run the expensive clone."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _state(supply):
    p = PlayerState(DummyAI())
    state = GameState([p])
    state.log_callback = lambda *_: None
    state.supply = dict(supply)
    return state, p


def test_gate_false_when_game_is_nowhere_near_ending():
    state, p = _state({"Province": 8, "Copper": 30})
    assert state._buy_could_end_game(p, get_card("Province")) is False


def test_gate_true_when_province_pile_is_low():
    state, p = _state({"Province": 2, "Copper": 30})
    assert state._buy_could_end_game(p, get_card("Province")) is True


def test_gate_true_when_colony_pile_is_low():
    state, p = _state({"Province": 8, "Colony": 2, "Copper": 30})
    assert state._buy_could_end_game(p, get_card("Copper")) is True


def test_gate_false_when_colony_not_in_supply():
    state, p = _state({"Province": 8, "Copper": 30})
    # Colony absent — its threshold must not falsely trigger
    assert state._buy_could_end_game(p, get_card("Copper")) is False


def test_gate_true_when_two_piles_already_empty():
    state, p = _state({"Province": 8, "Copper": 30, "Village": 0, "Smithy": 0})
    assert state._buy_could_end_game(p, get_card("Copper")) is True
```

### Step 2 — run the test, verify it fails

Run: `pytest tests/test_endgame_purchase_guard_gate.py -v`

Expected: all fail with `AttributeError: '_buy_could_end_game'`.

### Step 3 — implement the gate

Add to `dominion/game/game_state.py` (place near the existing `_normal_game_end_reached`):

```python
def _buy_could_end_game(self, player: PlayerState, card: "Card") -> bool:
    """Loose *necessary* condition: could this buy plausibly end the game?

    A pure, cheap pre-check that gates the expensive deep-copy +
    real-buy simulation in :meth:`gain_would_lose_game`. May trigger
    unnecessary copies (harmless), but must never skip a buy that
    could end the game — so the thresholds are conservative.

    The thresholds are loose because the buy can plausibly trigger
    side-effect gains (e.g. Border Village, Hoard with a Victory buy)
    that empty a pile we wouldn't predict from the card alone.
    """
    if self.supply.get("Province", 0) <= 2:
        return True
    if "Colony" in self.supply and self.supply["Colony"] <= 2:
        return True
    if self.empty_piles >= 2:
        return True
    return False
```

### Step 4 — run the test, verify it passes

Run: `pytest tests/test_endgame_purchase_guard_gate.py -v`

Expected: all five pass.

### Step 5 — commit

```bash
git add dominion/game/game_state.py tests/test_endgame_purchase_guard_gate.py
git commit -m "Add _buy_could_end_game cheap gate for the endgame guard"
```

---

## Task 3: `_all_decision_hooks_pure` + the RL boundary flag

**Files:**
- Modify: `dominion/game/game_state.py` (add `_all_decision_hooks_pure` method).
- Modify: `dominion/rl/rl_ai.py` (add class attribute `decision_hooks_are_pure = False`).
- Test: `tests/test_endgame_purchase_guard_purity.py` (new file).

### Step 1 — write the failing test

```python
"""The Option-1 correctness boundary: skip the guard for non-pure AIs."""

from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def test_purity_default_true_for_baseline_ai():
    state = GameState([PlayerState(DummyAI()), PlayerState(DummyAI())])
    assert state._all_decision_hooks_pure() is True


def test_purity_false_when_any_ai_opts_out():
    p1 = PlayerState(DummyAI())
    p2 = PlayerState(DummyAI())
    p2.ai.decision_hooks_are_pure = False
    state = GameState([p1, p2])
    assert state._all_decision_hooks_pure() is False


def test_rl_ai_class_marks_itself_impure():
    # The RL agent overrides the default at the class level. Importing it
    # here keeps the dependency one-directional (the guard checks an
    # attribute; it does not import RL).
    from dominion.rl.rl_ai import RLAI

    assert getattr(RLAI, "decision_hooks_are_pure", True) is False
```

### Step 2 — run the test, verify it fails

Run: `pytest tests/test_endgame_purchase_guard_purity.py -v`

Expected: `_all_decision_hooks_pure` missing (AttributeError), and `RLAI` lacks the flag.

### Step 3 — implement

Add to `dominion/game/game_state.py`:

```python
def _all_decision_hooks_pure(self) -> bool:
    """True iff every player's AI declares its decision hooks pure.

    The endgame-loss guard runs the *real* buy on a clone of the state;
    along the way it calls AI decision hooks (e.g.
    ``should_reveal_trader``, ``should_exchange_changeling``, overpay
    prompts) on the shared-by-reference AI. For genetic / strategy-based
    AIs these are pure priority-rule queries. For RL agents they may
    hold/mutate network state, so the guard cleanly disables itself by
    returning False here.
    """
    return all(
        getattr(p.ai, "decision_hooks_are_pure", True)
        for p in self.players
    )
```

Edit `dominion/rl/rl_ai.py` to add (near the top of the `RLAI` class body):

```python
class RLAI(...):
    # Endgame-loss guard boundary: RL decision hooks may mutate network
    # state, so the guard skips RL games rather than risk corruption.
    decision_hooks_are_pure = False

    # ... existing body ...
```

(Exact placement: read the file first; place the attribute directly under the class header before `__init__`.)

### Step 4 — run the test, verify it passes

Run: `pytest tests/test_endgame_purchase_guard_purity.py -v`

Expected: all three pass.

### Step 5 — commit

```bash
git add dominion/game/game_state.py dominion/rl/rl_ai.py tests/test_endgame_purchase_guard_purity.py
git commit -m "Add purity boundary so endgame guard skips RL games"
```

---

## Task 4: Extract `_commit_buy` from `handle_buy_phase` (behavior-preserving refactor)

**Files:**
- Modify: `dominion/game/game_state.py` — extract the per-card buy commit body from `handle_buy_phase` into a new `_commit_buy(player, card)` method; replace the inline block with a call.
- Test: existing tests (no new tests; this is a refactor verified by `pytest -q`).

### Step 1 — read the existing block

```bash
sed -n '2030,2120p' dominion/game/game_state.py
```

The block to extract starts immediately after `choice = self._choose_safe_buy(player, affordable)` / `if choice is None: break`, and ends before the loop's next iteration. It comprises: metric bookkeeping, cost computation, debit, log, `bought_this_turn`, `coins_spent_this_turn`, potions/coin_tokens, overpay prompt, the `if/elif` for events/projects/normal-card, `on_buy`, `gain_card`, in-play hooks, adventures attack, etc.

### Step 2 — write a focused test that calls `_commit_buy` directly

Add to `tests/test_endgame_purchase_guard_clone.py` (or a new file `tests/test_commit_buy.py`):

```python
def test_commit_buy_decrements_supply_and_records_buy():
    """`_commit_buy` runs exactly one buy commit: supply -1, card in
    discard / bought_this_turn / coins spent. This is the same code path
    the buy phase uses for each AI buy choice."""
    p = PlayerState(DummyAI())
    state = GameState([p])
    state.log_callback = lambda *_: None
    state.supply = {"Silver": 10, "Copper": 30}
    p.coins = 3
    p.buys = 1

    state._commit_buy(p, get_card("Silver"))

    assert state.supply["Silver"] == 9
    assert "Silver" in p.bought_this_turn
    assert p.coins == 0
    assert any(c.name == "Silver" for c in p.discard)
```

### Step 3 — run the test, verify it fails

Run: `pytest tests/test_commit_buy.py -v`

Expected: `AttributeError: '_commit_buy'`.

### Step 4 — extract the method

Replace the body of `handle_buy_phase`'s per-buy block with a call to `_commit_buy(player, choice)`, and define `_commit_buy(self, player, card)` with the moved body. The method must operate on the `(self, player, card)` parameters only — no closure over loop-local variables — so the same call works on a clone.

Pseudocode for the extracted method (preserve exact existing logic; this is shape, not a rewrite):

```python
def _commit_buy(self, player: PlayerState, card: "Card") -> None:
    """Execute exactly one buy of ``card`` for ``player``.

    Single source of truth for "what buying a card does", shared by
    :meth:`handle_buy_phase` and the endgame guard's simulated buy.
    Includes: metric bookkeeping, cost payment (coins + coin_tokens +
    potions), debt, bought_this_turn, on_buy hook, supply decrement,
    gain_card (which fires landmark/ally/project on_gain hooks, Trader/
    Changeling/Exile reactions, Watchtower/Royal Seal, etc.), Guilds
    overpay, in-play on-buy hooks (Hoard/Talisman), Adventures
    on-buy attacks.
    """
    # [existing block from handle_buy_phase, parameterised on (player, card)]
```

In `handle_buy_phase` the buy-loop body becomes (roughly):

```python
choice = self._choose_safe_buy(player, affordable)
if choice is None:
    break
self._commit_buy(player, choice)
```

### Step 5 — run the test + full suite, verify all green

```bash
pytest tests/test_commit_buy.py -v
pytest -q -p no:cacheprovider -m "not slow"
```

Expected: new test passes; existing full non-slow suite still green (this is a behavior-preserving refactor — no test should change).

### Step 6 — commit

```bash
git add dominion/game/game_state.py tests/test_commit_buy.py
git commit -m "Extract _commit_buy from handle_buy_phase as single source of truth"
```

---

## Task 5: New behavior tests for the real-buy-simulation guard (RED)

These tests are written **before** the rewrite in Task 6. They will fail against the current (enumeration-based) implementation in the ways described — that's the RED.

**Files:**
- Modify: `tests/test_endgame_purchase_guard.py` (add new test cases at the bottom).

### Step 1 — add the new tests

Append to `tests/test_endgame_purchase_guard.py`:

```python
def test_false_negative_blocked_when_hoard_empties_third_pile(monkeypatch):
    """Hoard in play gains a Gold for each Victory bought. Buying a
    Province while Gold is at 1 empties the Gold pile in the real buy
    path, which combined with two already-empty kingdom piles ends the
    game on a 3-pile-out. The enumeration model could not see this and
    would commit the losing buy; the real-buy guard correctly vetoes.
    """
    ai = PriorityBuyAI(["Province", "Copper"])
    state, me, _opp = make_state(ai, opponent_deck=provinces(4))
    state.supply = {
        "Province": 8,
        "Gold": 1,
        "Village": 0,
        "Smithy": 0,
        "Copper": 30,
    }
    me.coins = 8
    me.buys = 1
    me.in_play = [get_card("Hoard")]

    state.handle_buy_phase()

    assert "Province" not in me.bought_this_turn  # losing 3-pile-out vetoed
    assert "Copper" in me.bought_this_turn  # next-best taken


def test_guard_disabled_when_any_ai_marks_decision_hooks_impure():
    """RL boundary: if any AI declares impure decision hooks, the guard
    stands down (cannot safely run the simulated buy)."""
    ai = PriorityBuyAI(["Province"])
    ai.decision_hooks_are_pure = False
    state, me, _opp = make_state(ai, opponent_deck=provinces(5))
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert "Province" in me.bought_this_turn  # guard disabled


def test_gain_would_lose_game_preserves_rng_state():
    """The simulated buy must not perturb the module-global RNG seen by
    the real game; gain_would_lose_game saves/restores random.getstate()
    around the simulation."""
    import random

    ai = PriorityBuyAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=provinces(5))
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    random.seed(12345)
    before = random.getstate()
    state.gain_would_lose_game(me, get_card("Province"))
    after = random.getstate()

    assert before == after


def test_temple_endgame_correctly_handled():
    """Temple grants VP from its pile tokens when gained. The enumeration
    model couldn't model card-specific on-gain VP (a documented v1 caveat);
    the real-buy guard does, so buying the last Temple while tied is
    correctly NOT vetoed when the bonus puts the buyer ahead."""
    ai = PriorityBuyAI(["Temple"])
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")])
    state.supply = {
        "Temple": 1,        # last Temple
        "Province": 8,
        "Village": 0,
        "Smithy": 0,        # two empty piles — Temple is the third
        "Copper": 30,
    }
    state.temple_pile_tokens = 3  # Temple awards 3 VP on gain
    me.coins = 5
    me.buys = 1

    state.handle_buy_phase()

    # me's real score after the buy: Temple card (1 VP) + 3 VP tokens = 4;
    # opp: 6. Still behind → guard should veto.
    assert "Temple" not in me.bought_this_turn
```

### Step 2 — run the new tests, verify the RED

Run: `pytest tests/test_endgame_purchase_guard.py -v -k "false_negative or impure or rng_state or temple_endgame"`

Historical RED expectations before Task 6:

- `test_false_negative_blocked_when_hoard_empties_third_pile` — **FAIL** (current enumeration model misses Hoard's pile-emptying side effect; Province gets bought).
- `test_guard_disabled_when_any_ai_marks_decision_hooks_impure` — likely PASS today only by coincidence; document expected; will be reasserted by Task 6 rewrite.
- `test_gain_would_lose_game_preserves_rng_state` — likely PASS today (sim doesn't consume RNG); the test pins the *invariant* and protects against future regressions.
- `test_temple_endgame_correctly_handled` — **FAIL** under the old enumeration model (Temple is a card, not a landmark; the old `_buy_pile_restorable` path didn't apply; the cheap sim added Temple to discard with no VP bonus, so the assertion could pass without exercising the intended real-buy path). After Task 6, this passes through the shared `_commit_buy` simulation.

### Step 3 — commit the new tests (RED for the real ones)

```bash
git add tests/test_endgame_purchase_guard.py
git commit -m "Add tests for real-buy-sim guard: false negative, RL boundary, RNG isolation, Temple"
```

---

## Task 6: Rewrite `gain_would_lose_game` to use the clone + real buy

**Files:**
- Modify: `dominion/game/game_state.py` — replace the body of `gain_would_lose_game`.

### Step 1 — confirm test contract

The contract that must hold after the rewrite:

- All 12 PR-#275 tests in `tests/test_endgame_purchase_guard.py` must remain green.
- The four new tests from Task 5 must go green.
- The two enumeration helpers (`_has_unmodeled_vp_on_gain`, `_buy_pile_restorable`) are unused after this task (we delete them in Task 7).

### Step 2 — read existing `gain_would_lose_game`

```bash
sed -n '2960,3020p' dominion/game/game_state.py
```

Keep: the signature, the `allow_losing_pileout` opt-out at the top, the `_supply_pile_name` resolution (still used to look up the pile), and the docstring updated.

### Step 3 — replace the body

Replace `gain_would_lose_game`'s body with:

```python
def gain_would_lose_game(self, player: PlayerState, card: "Card") -> bool:
    """True if committing ``card`` to ``player`` would end the game with
    ``player`` not strictly ahead.

    Authoritative: performs the *real* buy on a deep copy of the game
    state and inspects the post-buy clone. The standard end condition
    and final scores are read from the clone, so every side effect that
    would happen in the real buy (VP-token hooks, Trader/Changeling/
    Exile reactions, on-buy/on-gain card effects, in-play hooks like
    Hoard/Talisman) is already applied — there is no model to diverge.

    A loose gate (:meth:`_buy_could_end_game`) keeps the expensive
    deep-copy off the hot path; for the vast majority of buys this
    returns ``False`` in constant time without ever cloning.

    The guard stands down (returns ``False``) when any AI declares its
    decision hooks impure (e.g. RL agents): the simulated buy on the
    shared-by-reference AI could otherwise mutate or thrash AI state.

    A tie counts as "would lose": the engine breaks ties by
    ``max(players, key=victory_points)``, i.e. seat order, which a
    strategy must not bank on.
    """
    if self._losing_pileout_allowed(player):
        return False

    if not self._all_decision_hooks_pure():
        return False

    if not self._buy_could_end_game(player, card):
        return False

    import random
    rng_state = random.getstate()
    try:
        clone = copy.deepcopy(self)
        clone_player = clone.players[self.players.index(player)]
        clone_card = type(card)() if not card.is_event and not card.is_project else card
        # For events/projects we keep the original card object — they
        # aren't cloned in the same way and their on_buy reads engine
        # state on the clone. For normal cards we instantiate a fresh
        # copy so the discard append in the clone uses an independent
        # object (matching how the real buy obtains the card from
        # supply).

        # Drain the buy resources we expect the buy loop to spend.
        # `_commit_buy` debits coins/coin_tokens/potions itself, so we
        # do not pre-debit here; it expects the player to be the buyer.
        clone._commit_buy(clone_player, clone_card)

        if not clone._normal_game_end_reached():
            return False
        my_vp = clone_player.get_victory_points(clone)
        opp_best = max(
            (p.get_victory_points(clone) for p in clone.players if p is not clone_player),
            default=0,
        )
        return my_vp <= opp_best
    finally:
        random.setstate(rng_state)
```

Notes on the `clone_card` line: review the existing `handle_buy_phase` to confirm how the card is obtained in the real path (likely via `get_card(name)` through `_get_affordable_cards`). If `_commit_buy` re-derives the card object as needed, you can skip the `type(card)()` step and just pass `card`. Adjust to match what the extracted `_commit_buy` expects. If unsure, use `get_card(card.name)` for normal cards.

### Step 4 — run the guard tests

```bash
pytest tests/test_endgame_purchase_guard.py -v
```

Expected: all 12 original + the 4 new (16 total) pass.

If a previously "guard skipped when X" test now fails because the real buy ends differently than the prior stand-down assumed, that's a *correctness improvement* — see Task 7 for the systematic adjustment.

### Step 5 — run the full non-slow suite

```bash
pytest -q -p no:cacheprovider -m "not slow"
```

Expected: green.

### Step 6 — commit

```bash
git add dominion/game/game_state.py
git commit -m "Rewrite gain_would_lose_game to run the real buy on a clone"
```

---

## Task 7: Adjust prior "guard skipped when X" tests for precise semantics

The PR-#275 tests `test_guard_skipped_when_trader_can_restore_pile`,
`test_guard_skipped_when_changeling_pile_available`, and
`test_guard_skipped_when_vp_awarding_landmark_in_play` passed via the
stand-down regardless of the AI's actual decision. Under the new design,
the simulated buy reflects the *real* AI decision:

- `should_reveal_trader` defaults to `False` → Trader does NOT exchange →
  pile depletes → game ends → buyer behind → **veto fires** (assertion in
  the old test, "Province bought", will fail).
- `should_exchange_changeling` defaults to `False` → ditto.
- Battlefield gives `+2` VP on Victory gain. With `opp = provinces(4) = 24`
  and `me = 0`, real buy yields `6 + 2 = 8 < 24` → veto fires; old
  assertion fails.

For each, choose the more meaningful update:

### Step 1 — Trader/Changeling: assert the precise no-veto path

Make the buyer's AI return `True` from `should_reveal_trader` /
`should_exchange_changeling`, so the simulated buy genuinely exchanges
and the pile is restored. Assert no veto then.

```python
class _RevealsTraderAI(PriorityBuyAI):
    def should_reveal_trader(self, state, player, gained_card, *, to_deck):
        return True


def test_guard_skipped_when_trader_can_restore_pile():
    ai = _RevealsTraderAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=provinces(4))
    state.supply = {"Province": 1, "Silver": 10, "Copper": 30}
    me.coins = 8
    me.buys = 1
    me.hand = [get_card("Trader")]

    state.handle_buy_phase()

    # Real buy exchanges Province for Silver, restoring Province to supply.
    # Game does not end → guard does not veto → the buy was "attempted"
    # (recorded in bought_this_turn) even though the gain became Silver.
    assert "Province" in me.bought_this_turn
    assert state.supply["Province"] == 1  # restored by Trader
    assert state.supply["Silver"] == 9    # Silver gained instead


class _ExchangesChangelingAI(PriorityBuyAI):
    def should_exchange_changeling(self, state, player, gained_card):
        return True


def test_guard_skipped_when_changeling_pile_available():
    ai = _ExchangesChangelingAI(["Province"])
    state, me, _opp = make_state(ai, opponent_deck=provinces(4))
    state.supply = {"Province": 1, "Changeling": 10, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert "Province" in me.bought_this_turn
    assert state.supply["Province"] == 1   # returned to pile via Changeling
    assert state.supply["Changeling"] == 9  # Changeling taken instead
```

### Step 2 — Battlefield: tighten the opp margin so +2 actually swings

```python
def test_guard_skipped_when_vp_awarding_landmark_in_play():
    from dominion.landmarks.landmarks import Battlefield

    ai = PriorityBuyAI(["Province"])
    # opp on 6 (one Province); me reaches 6 by card VP, +2 Battlefield = 8 → ahead.
    state, me, _opp = make_state(ai, opponent_deck=[get_card("Province")])
    state.landmarks = [Battlefield()]
    state.supply = {"Province": 1, "Copper": 30}
    me.coins = 8
    me.buys = 1

    state.handle_buy_phase()

    assert state.supply["Province"] == 0
    assert "Province" in me.bought_this_turn
```

### Step 3 — run guard tests

```bash
pytest tests/test_endgame_purchase_guard.py -v
```

Expected: all green.

### Step 4 — commit

```bash
git add tests/test_endgame_purchase_guard.py
git commit -m "Tighten Trader/Changeling/Battlefield tests for precise-sim semantics"
```

---

## Task 8: Delete the enumeration helpers

**Files:**
- Modify: `dominion/game/game_state.py` — delete `_has_unmodeled_vp_on_gain` and `_buy_pile_restorable`.

### Step 1 — confirm no remaining callers

```bash
grep -rn "_has_unmodeled_vp_on_gain\|_buy_pile_restorable" dominion tests
```

Expected: zero matches outside `game_state.py`'s own definitions and any references inside `gain_would_lose_game` which were removed in Task 6.

### Step 2 — delete the two methods

Remove the `def _has_unmodeled_vp_on_gain(...)` and `def _buy_pile_restorable(...)` definitions wholesale from `dominion/game/game_state.py`.

### Step 3 — run the full non-slow suite

```bash
pytest -q -p no:cacheprovider -m "not slow"
```

Expected: green.

### Step 4 — commit

```bash
git add dominion/game/game_state.py
git commit -m "Remove enumeration-based guard helpers (replaced by real-buy sim)"
```

---

## Task 9: Slow-suite + ad-hoc perf check

**Files:**
- No source changes if perf is fine.
- If perf regression > ~15%: tighten the gate (e.g. lower the `Province ≤ 2`/`Colony ≤ 2`/`empty_piles ≥ 2` thresholds, or add an early-exit when `Province > 4 and empty_piles == 0`). **Never** relax correctness to recover performance.

### Step 1 — baseline timing

If not already recorded for the `cd76f7e` commit, capture a baseline by checking out `main` in a sibling checkout and timing the slow suite:

```bash
# from any clean main checkout
time pytest -q -p no:cacheprovider -m "slow"
```

Record the wall-clock figure (e.g. `~22s`).

### Step 2 — measure post-rewrite

```bash
time pytest -q -p no:cacheprovider -m "slow"
```

Expected: regression **< ~15%** vs the baseline.

### Step 3 — ad-hoc GA timing sanity check

Pick a small genetic-trainer run (refer to `dominion/simulation/genetic_trainer.py` for invocation), time before and after. Confirm copies stay rare.

```bash
# Example (adjust to the project's actual entrypoint)
time python -c "from dominion.simulation.genetic_trainer import ... ; run(games=50)"
```

### Step 4 — if perf is fine: commit a tiny note

If you tightened the gate as a result, commit those edits with a message describing the new threshold.

```bash
git add dominion/game/game_state.py
git commit -m "Tighten endgame-guard gate after perf measurement"
```

If no changes needed, this task produces no commit — just a confirmation that the bar is met.

---

## Task 10: Final cross-check, open PR

### Step 1 — full suite incl. slow

```bash
pytest -q -p no:cacheprovider
```

Expected: green.

### Step 2 — diff sanity-check

```bash
git log --oneline cd76f7e..HEAD
git diff --stat cd76f7e
```

Confirm: the diff is a clean refactor — additions for the new methods, deletions of the two enumeration helpers, body of `gain_would_lose_game` replaced, new tests added, existing tests adjusted in Task 7.

### Step 3 — push and open PR

```bash
git push -u origin start-philadelphia-claude
gh pr create --base main --title "Endgame guard: real-buy simulation replaces enumeration" --body "$(cat <<'EOF'
Replaces the enumeration-based endgame-loss guard (merged in #275) with a real-buy simulation: clone the state, run the actual buy via a shared `_commit_buy` entry point, evaluate end-condition and scores on the post-buy clone. Eliminates the false-veto whack-a-mole (3 review rounds on #275) and the false-negative direction the prior approach could not catch.

Design: `docs/plans/2026-05-19-endgame-guard-real-simulation-design.md`.

Notes: gated by a cheap "game is near ending" pre-check so the deepcopy stays off the hot path; RL games opt out via `decision_hooks_are_pure = False`; RNG saved/restored around the simulation. `_has_unmodeled_vp_on_gain` and `_buy_pile_restorable` deleted.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### Step 4 — done

Wait for CI + reviewer. Address any review comments using @superpowers:receiving-code-review.

---

## References

- Design doc: `docs/plans/2026-05-19-endgame-guard-real-simulation-design.md`
- Interim PR (now in main): `cd76f7e Veto buys that would end the game while losing (#275)`
- TDD discipline throughout: @superpowers:test-driven-development
