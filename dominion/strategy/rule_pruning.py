"""Profile-based pruning of unfired priority rules.

This complements :mod:`dominion.strategy.genome_simplification`:

- ``genome_simplification`` is *syntactic* — it removes rules that are
  provably dead by reading the priority list alone (dupes, rules behind
  an earlier unconditional rule for the same card).
- ``rule_pruning`` is *empirical* — it relies on the priority walker
  having recorded which rules actually fired during play
  (``rule._fired = True`` in :meth:`EnhancedStrategy._choose_from_priority`),
  and drops rules that never fired across an entire fitness-eval window.

The empirical pass catches dead rules that the syntactic pass cannot:
cards dominated by cheaper alternatives at the same affordability tier
(e.g., Investment $4 dominated by Clerk $4 when Clerk is higher in the
list), or condition-gated rules whose condition never passes in real
games (e.g., Platinum gated to ``turn<=11`` when the engine never
reaches $9 before turn 11).

Usage during GA evolution:

1. Call :func:`reset_fire_flags` on each strategy at the start of its
   fitness evaluation.
2. The walker records fires in-place across all eval games.
3. After the eval window, call :func:`prune_unfired_rules` on the
   strategy to drop dead rules before crossover/mutation.

The pruner is gated by a ``min_rules`` floor so it cannot shrink a
priority list below a safe minimum even when all rules happen to be
unfired (e.g., during the very first generation of a fresh population).
"""

from __future__ import annotations

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


_PRIORITY_LIST_ATTRS = (
    "gain_priority",
    "action_priority",
    "treasure_priority",
    "trash_priority",
)


def reset_fire_flags(strategy: EnhancedStrategy) -> None:
    """Clear ``_fired`` on every rule of every priority list."""
    for attr in _PRIORITY_LIST_ATTRS:
        for rule in getattr(strategy, attr, []) or []:
            rule._fired = False


def _prune_list(rules: list[PriorityRule], min_rules: int) -> list[PriorityRule]:
    """Keep all fired rules in order; pad with unfired rules from the head
    of the original list to satisfy the ``min_rules`` floor."""
    fired = [r for r in rules if getattr(r, "_fired", False)]
    if len(fired) >= min_rules:
        return fired

    # Need padding — walk the original list in order and add unfired
    # rules until we hit the floor. Preserve original ordering by emitting
    # rules in their original positions, but only as many unfired ones as
    # required to fill the gap.
    pad_needed = min_rules - len(fired)
    output: list[PriorityRule] = []
    pad_remaining = pad_needed
    for r in rules:
        if getattr(r, "_fired", False):
            output.append(r)
        elif pad_remaining > 0:
            output.append(r)
            pad_remaining -= 1
    return output


def prune_unfired_rules(
    strategy: EnhancedStrategy,
    *,
    min_rules: int = 0,
) -> None:
    """Drop rules with ``_fired == False`` from every priority list on the
    strategy, in place. Rules without an explicit ``_fired`` attribute are
    treated as unfired.

    The ``min_rules`` floor preserves at least that many rules per list:
    if pruning would shrink a list below the floor, unfired rules from
    the head of the original list are retained (in their original order)
    until the floor is met. This guards against accidentally emptying a
    priority list before the walker has had a chance to exercise it
    (e.g., during the very first generation of a freshly randomised
    population).
    """
    for attr in _PRIORITY_LIST_ATTRS:
        rules = getattr(strategy, attr, None)
        if not rules:
            continue
        setattr(strategy, attr, _prune_list(list(rules), min_rules))
