"""Structured "buy menu" genome operators for the genetic trainer.

The free-form genome let mutation draw arbitrary conditions from a large
vocabulary and assemble gain lists in any order — so random individuals
opened with Copper above Province, champions accumulated duplicate rules,
and almost every mutation was noise. These operators constrain the search
space the way a strong player thinks about a kingdom:

- a gain list is a *menu*: a greening block (Province / Duchy / Estate with
  pile-count gates) over an economy backbone (Gold / Silver) interleaved
  with a handful of kingdom picks, each capped with ``max_in_deck``;
- mutations are menu edits — reorder entries, nudge a cap, swap a gate from
  a small curated vocabulary, add or drop a pick — instead of arbitrary
  condition rewrites;
- normalization enforces invariants every viable strategy needs (a Province
  rule exists, no duplicate rules, basic treasures are playable).

The phenotype is still a plain :class:`EnhancedStrategy` rule list, so
seeds, serialization, pruning, and simplification all keep working; only
how the GA *moves through* strategy space changes.
"""

from __future__ import annotations

import random as _random_module
import re
from dataclasses import dataclass, field

from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy

# Cards handled by the menu skeleton rather than treated as kingdom picks.
BASIC_CARDS = {"Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"}

_MAX_IN_DECK_RE = re.compile(r"PriorityRule\.max_in_deck\('([^']+)', (\d+)\)")


@dataclass
class KingdomInfo:
    """Card-role classification for one kingdom, used to build sane menus."""

    kingdom_cards: list[str]
    gainable: list[str] = field(default_factory=list)  # kingdom cards worth a menu slot
    action_cards: list[str] = field(default_factory=list)
    treasure_cards: list[str] = field(default_factory=list)
    villages: list[str] = field(default_factory=list)      # +2 or more actions
    cantrips: list[str] = field(default_factory=list)      # exactly +1 action
    terminal_draw: list[str] = field(default_factory=list)  # 0 actions, +2 or more cards
    other_terminals: list[str] = field(default_factory=list)
    costs: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_kingdom(cls, kingdom_cards: list[str]) -> "KingdomInfo":
        info = cls(kingdom_cards=list(kingdom_cards))
        for name in kingdom_cards:
            if name in BASIC_CARDS:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            info.costs[name] = card.cost.coins
            info.gainable.append(name)
            if card.is_action:
                info.action_cards.append(name)
                if card.stats.actions >= 2:
                    info.villages.append(name)
                elif card.stats.actions == 1:
                    info.cantrips.append(name)
                elif card.stats.cards >= 2:
                    info.terminal_draw.append(name)
                else:
                    info.other_terminals.append(name)
            if card.is_treasure:
                info.treasure_cards.append(name)
        return info

    def default_cap(self, card: str, rng) -> int:
        """A sensible max-in-deck cap range per card role."""
        if card in self.villages:
            return rng.randint(2, 4)
        if card in self.terminal_draw:
            return rng.randint(1, 3)
        if card in self.other_terminals:
            return rng.randint(1, 2)
        if card in self.cantrips:
            return rng.randint(2, 5)
        if card in self.treasure_cards:
            return rng.randint(1, 3)
        # Victory/other kingdom cards (Gardens, Mill, ...) — wide range.
        return rng.randint(1, 8)


# ---------------------------------------------------------------------------
# Curated gate vocabulary
# ---------------------------------------------------------------------------


def _greening_gate(card: str, rng):
    if card == "Duchy":
        return PriorityRule.provinces_left("<=", rng.randint(3, 6))
    if card == "Estate":
        return PriorityRule.provinces_left("<=", rng.randint(1, 3))
    # Province: usually unconditional; occasionally an endgame-only gate.
    if rng.random() < 0.85:
        return None
    return PriorityRule.provinces_left("<=", rng.randint(4, 8))


def _silver_gate(rng):
    roll = rng.random()
    if roll < 0.4:
        return None
    if roll < 0.7:
        return PriorityRule.turn_number("<=", rng.randint(5, 12))
    return PriorityRule.provinces_left(">", rng.randint(2, 4))


def _pick_gate(card: str, info: KingdomInfo, rng):
    """Cap + optional extra gate for a kingdom menu pick."""
    cap = PriorityRule.max_in_deck(card, info.default_cap(card, rng))
    if rng.random() >= 0.3:
        return cap
    roll = rng.random()
    if roll < 0.5:
        extra = PriorityRule.turn_number("<=", rng.randint(6, 16))
    elif roll < 0.8 and len(info.gainable) >= 2:
        anchor = rng.choice([c for c in info.gainable if c != card] or [card])
        extra = PriorityRule.has_cards([anchor], rng.randint(1, 2))
    else:
        extra = PriorityRule.provinces_left(">", rng.randint(2, 4))
    return PriorityRule.and_(cap, extra)


def _gate_for(card: str, info: KingdomInfo, rng):
    """Re-gate vocabulary used by mutation, dispatched on the card's role."""
    if card in ("Province", "Duchy", "Estate"):
        return _greening_gate(card, rng)
    if card == "Silver":
        return _silver_gate(rng)
    if card == "Gold":
        return None if rng.random() < 0.8 else PriorityRule.max_in_deck("Gold", rng.randint(2, 6))
    if card == "Copper":
        # Copper is only ever bought deliberately (e.g. Gardens piles) —
        # always keep it gated so it can't become an unconditional junk buy.
        return PriorityRule.has_cards(["Gardens"], 1) if "Gardens" in info.gainable else PriorityRule.provinces_left("<=", 1)
    return _pick_gate(card, info, rng)


# ---------------------------------------------------------------------------
# Random initialization
# ---------------------------------------------------------------------------


def random_menu_strategy(info: KingdomInfo, rng=_random_module) -> BaseStrategy:
    """Build a random but *coherent* strategy: greening block on top, an
    economy backbone, and a few capped kingdom picks ordered roughly by cost."""
    strategy = BaseStrategy()

    gain: list[PriorityRule] = [PriorityRule("Province")]
    if rng.random() < 0.9:
        gain.append(PriorityRule("Duchy", _greening_gate("Duchy", rng)))
    if rng.random() < 0.4:
        gain.append(PriorityRule("Estate", _greening_gate("Estate", rng)))

    picks: list[str] = []
    if info.gainable:
        hi = min(6, len(info.gainable))
        n_picks = rng.randint(min(2, hi), hi)
        picks = rng.sample(info.gainable, n_picks)

    # Merge picks with the treasure backbone, ordered by cost with jitter so
    # adjacent-cost cards can swap order between individuals.
    entries: list[tuple[float, PriorityRule]] = [
        (info.costs.get(card, 0) + rng.uniform(-1.5, 1.5), PriorityRule(card, _pick_gate(card, info, rng)))
        for card in picks
    ]
    entries.append((6 + rng.uniform(-1.5, 1.5), PriorityRule("Gold")))
    entries.append((3 + rng.uniform(-1.5, 1.5), PriorityRule("Silver", _silver_gate(rng))))
    entries.sort(key=lambda pair: pair[0], reverse=True)
    gain.extend(rule for _, rule in entries)
    strategy.gain_priority = gain

    # Action play order: villages first, then cantrips, then terminal draw,
    # then remaining terminals. Within each role group the order is shuffled.
    action: list[PriorityRule] = []
    for group in (info.villages, info.cantrips, info.terminal_draw, info.other_terminals):
        group = list(group)
        rng.shuffle(group)
        action.extend(PriorityRule(card) for card in group)
    strategy.action_priority = action

    # Treasures: Gold, kingdom treasures (cost order), Silver, Copper.
    kingdom_treasures = sorted(info.treasure_cards, key=lambda c: -info.costs.get(c, 0))
    strategy.treasure_priority = (
        [PriorityRule("Gold")]
        + [PriorityRule(c) for c in kingdom_treasures]
        + [PriorityRule("Silver"), PriorityRule("Copper")]
    )

    strategy.trash_priority = [
        PriorityRule("Curse"),
        PriorityRule("Estate", PriorityRule.provinces_left(">", rng.randint(2, 6))),
        PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], rng.randint(2, 4))),
    ]

    strategy.way_policy = []
    return strategy


# ---------------------------------------------------------------------------
# Menu-aware mutation
# ---------------------------------------------------------------------------


def _adjust_cap(rule: PriorityRule, rng) -> bool:
    """Nudge a max_in_deck cap on this rule by ±1. Returns True if adjusted."""
    source = getattr(rule.condition, "_source", "") if rule.condition else ""
    match = _MAX_IN_DECK_RE.search(source)
    if not match:
        return False
    card, cap = match.group(1), int(match.group(2))
    new_cap = max(1, min(10, cap + rng.choice([-1, 1])))
    if new_cap == cap:
        return False
    new_inner = PriorityRule.max_in_deck(card, new_cap)
    # Preserve a compound gate's other condition by rebuilding the and_ with
    # the new cap source spliced in is not worth the complexity — the curated
    # vocabulary is small, so replacing the whole condition keeps genomes lean.
    rule.condition = new_inner
    return True


def mutate_menu(strategy: BaseStrategy, info: KingdomInfo, rate: float, rng=_random_module) -> BaseStrategy:
    """Apply menu-edit mutations in place and return the strategy."""
    gain = strategy.gain_priority

    # Reorder: swap adjacent entries.
    if rng.random() < rate and len(gain) >= 2:
        i = rng.randint(0, len(gain) - 2)
        gain[i], gain[i + 1] = gain[i + 1], gain[i]

    # Relocate one entry.
    if rng.random() < rate * 0.5 and len(gain) >= 2:
        i = rng.randint(0, len(gain) - 1)
        rule = gain.pop(i)
        gain.insert(rng.randint(0, len(gain)), rule)

    # Nudge a cap.
    if rng.random() < rate and gain:
        capped = [r for r in gain if _MAX_IN_DECK_RE.search(getattr(r.condition, "_source", "") if r.condition else "")]
        if capped:
            _adjust_cap(rng.choice(capped), rng)

    # Add a missing kingdom pick.
    if rng.random() < rate * 0.4:
        existing = {r.card_name for r in gain}
        missing = [c for c in info.gainable if c not in existing]
        if missing:
            card = rng.choice(missing)
            gain.insert(rng.randint(0, len(gain)), PriorityRule(card, _pick_gate(card, info, rng)))

    # Drop an entry (never Province; keep a minimum menu).
    if rng.random() < rate * 0.25 and len(gain) > 4:
        droppable = [i for i, r in enumerate(gain) if r.card_name != "Province"]
        if droppable:
            gain.pop(rng.choice(droppable))

    # Re-gate one entry from the curated vocabulary for its role.
    if rng.random() < rate and gain:
        rule = rng.choice(gain)
        rule.condition = _gate_for(rule.card_name, info, rng)

    # Action play order: swap adjacent; occasionally add/remove.
    action = strategy.action_priority
    if rng.random() < rate and len(action) >= 2:
        i = rng.randint(0, len(action) - 2)
        action[i], action[i + 1] = action[i + 1], action[i]
    if rng.random() < rate * 0.3:
        existing = {r.card_name for r in action}
        missing = [c for c in info.action_cards if c not in existing]
        if missing:
            card = rng.choice(missing)
            action.insert(rng.randint(0, len(action)), PriorityRule(card))
    if rng.random() < rate * 0.2 and len(action) > 1:
        action.pop(rng.randint(0, len(action) - 1))

    # Treasure order: swap adjacent.
    treasure = strategy.treasure_priority
    if rng.random() < rate * 0.5 and len(treasure) >= 2:
        i = rng.randint(0, len(treasure) - 2)
        treasure[i], treasure[i + 1] = treasure[i + 1], treasure[i]

    # Trash thresholds.
    if rng.random() < rate:
        for rule in strategy.trash_priority:
            if rng.random() >= 0.3:
                continue
            if rule.card_name == "Estate":
                rule.condition = PriorityRule.provinces_left(">", rng.randint(2, 6))
            elif rule.card_name == "Copper":
                rule.condition = PriorityRule.has_cards(["Silver", "Gold"], rng.randint(2, 4))

    return strategy


# ---------------------------------------------------------------------------
# Normalization invariants
# ---------------------------------------------------------------------------


def normalize_menu(strategy: BaseStrategy, info: KingdomInfo) -> BaseStrategy:
    """Enforce the invariants every viable menu needs.

    - exactly no duplicate (card, gate) rules — crossover splices can clone;
    - a Province gain rule exists (without one the strategy cannot win);
    - never an unconditional Copper/Curse gain rule (pure junk buys);
    - Gold/Silver/Copper present in treasure_priority so coins get played.
    """
    seen: set[tuple] = set()
    deduped: list[PriorityRule] = []
    for rule in strategy.gain_priority:
        if rule.card_name == "Curse":
            continue
        if rule.card_name == "Copper" and rule.condition is None:
            continue
        key = (rule.card_name, getattr(rule.condition, "_source", None) if rule.condition else None)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rule)
    strategy.gain_priority = deduped

    if not any(r.card_name == "Province" for r in strategy.gain_priority):
        strategy.gain_priority.insert(0, PriorityRule("Province"))

    treasure_names = {r.card_name for r in strategy.treasure_priority}
    for name in ("Gold", "Silver", "Copper"):
        if name not in treasure_names:
            strategy.treasure_priority.append(PriorityRule(name))

    return strategy


# ---------------------------------------------------------------------------
# Kingdom-aware similarity (for fitness sharing)
# ---------------------------------------------------------------------------


def _top_kingdom_picks(strategy: BaseStrategy, n: int = 5) -> set[str]:
    picks: list[str] = []
    for rule in strategy.gain_priority:
        if rule.card_name in BASIC_CARDS or rule.card_name in picks:
            continue
        picks.append(rule.card_name)
        if len(picks) == n:
            break
    return set(picks)


def kingdom_similarity(a: BaseStrategy, b: BaseStrategy) -> float:
    """Top-5 overlap of *kingdom* gain picks, ignoring the shared skeleton.

    Structured menus all contain Province/Duchy/Gold/Silver, so similarity
    computed over raw top-5 entries would put nearly every individual in one
    niche and fitness sharing would punish the whole population uniformly.
    What distinguishes strategies is which kingdom cards they pick, in
    priority order."""
    top_a = _top_kingdom_picks(a)
    top_b = _top_kingdom_picks(b)
    if not top_a and not top_b:
        return 1.0
    denom = max(1, min(5, max(len(top_a), len(top_b))))
    return len(top_a & top_b) / denom
