"""Behavior-preserving simplification of evolved priority lists.

The genetic trainer's mutation/crossover operators tend to accumulate dead
rules — duplicates of earlier rules and rules unreachable behind an earlier
unconditional rule for the same card. These rules can never affect any
decision (the priority resolver returns the first matching rule), but they
inflate the genome and dilute the effect of mutation. This module strips
them out without changing strategy behavior.

What is and isn't simplified
----------------------------
Two transformations are applied, in order, to each priority list:

1. **Dedupe.** A rule with the same ``(card, condition._source)`` as an
   earlier rule in the list is dropped. The first occurrence wins.
2. **Unconditional dominance.** Once an unconditional rule (``condition is
   None``) appears for a given card, every later rule for that same card is
   unreachable and is dropped.

Conditions are compared by their ``_source`` string (set by
``PriorityRule._tag_source``). Two conditions with identical source are
treated as equal; ``None`` matches ``None`` only.

Tautology removal (e.g., stripping ``resources('coins','>=',8)`` from
Province rules because Province is only in the choices when affordable) is
intentionally **not** done here, because removing such a condition can
subtly change behavior when Coffer tokens bridge the affordability gap.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Optional

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _condition_signature(rule: PriorityRule) -> Optional[str]:
    """Stable string identity for a rule's condition; None if unconditional."""
    cond = rule.condition
    if cond is None:
        return None
    return getattr(cond, "_source", repr(cond))


def _simplify_priority_list(rules: Iterable[PriorityRule]) -> list[PriorityRule]:
    """Apply dedupe + unconditional-dominance to a single priority list."""
    seen_signatures: set[tuple[str, Optional[str]]] = set()
    cards_with_unconditional: set[str] = set()
    output: list[PriorityRule] = []

    for rule in rules:
        # Drop rules dominated by a prior unconditional rule for the same card.
        if rule.card in cards_with_unconditional:
            continue

        # Drop rules with the same (card, condition) signature as a prior rule.
        sig = (rule.card, _condition_signature(rule))
        if sig in seen_signatures:
            continue

        output.append(rule)
        seen_signatures.add(sig)

        if rule.condition is None:
            cards_with_unconditional.add(rule.card)

    return output


def simplify_strategy(strategy: EnhancedStrategy) -> EnhancedStrategy:
    """Return a deep copy of ``strategy`` with each priority list simplified.

    The input is not mutated. Behavior of the returned strategy is identical
    to the input under the priority resolver in
    ``EnhancedStrategy._choose_from_priority``.
    """
    out = deepcopy(strategy)
    out.gain_priority = _simplify_priority_list(out.gain_priority)
    out.action_priority = _simplify_priority_list(out.action_priority)
    out.treasure_priority = _simplify_priority_list(out.treasure_priority)
    out.trash_priority = _simplify_priority_list(out.trash_priority)
    return out
