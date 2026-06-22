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
BASIC_CARDS = {"Copper", "Silver", "Gold", "Platinum", "Estate", "Duchy", "Province", "Colony", "Curse"}

# Unconditional rules for these shadow every cheaper buy below them, so the
# greening block must always sort above them (see normalize_menu).
_BASIC_TREASURES = ("Gold", "Silver", "Platinum")

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
    has_colony: bool = False
    has_platinum: bool = False

    @classmethod
    def from_kingdom(cls, kingdom_cards: list[str]) -> "KingdomInfo":
        info = cls(kingdom_cards=list(kingdom_cards))
        for name in kingdom_cards:
            if name == "Colony":
                info.has_colony = True
            elif name == "Platinum":
                info.has_platinum = True
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
    if card == "Colony":
        # Colony is the win condition on Colony boards — keep it ungated.
        return None
    if card == "Silver":
        return _silver_gate(rng)
    if card in ("Gold", "Platinum"):
        return None if rng.random() < 0.8 else PriorityRule.max_in_deck(card, rng.randint(2, 6))
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

    gain: list[PriorityRule] = []
    if info.has_colony:
        gain.append(PriorityRule("Colony"))
    gain.append(PriorityRule("Province"))
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
    if info.has_platinum:
        entries.append((9 + rng.uniform(-1.5, 1.5), PriorityRule("Platinum")))
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

    # Treasures: Platinum, Gold, kingdom treasures (cost order), Silver, Copper.
    kingdom_treasures = sorted(info.treasure_cards, key=lambda c: -info.costs.get(c, 0))
    strategy.treasure_priority = (
        ([PriorityRule("Platinum")] if info.has_platinum else [])
        + [PriorityRule("Gold")]
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


def _action_role_rank(card: str, info: KingdomInfo) -> int:
    """Return the structured action-order rank for ``card``.

    Lower ranks play earlier. This intentionally mirrors random initialization:
    action providers first, then cantrips, then terminal draw, then other
    terminals.

    Cards in the kingdom are classified from ``info``. A rule may also reference
    a registry-known action that is not in the kingdom (e.g. Horse gained off
    the board); those are classified by their own card stats with the same
    thresholds ``KingdomInfo.from_kingdom`` uses, so a non-kingdom cantrip is
    not forced behind every kingdom terminal. Truly unknown cards go last so
    they cannot disrupt known safe order.
    """
    if card in info.villages:
        return 0
    if card in info.cantrips:
        return 1
    if card in info.terminal_draw:
        return 2
    if card in info.other_terminals:
        return 3
    return _stats_role_rank(card)


def _stats_role_rank(card: str) -> int:
    """Rank a registry-known action by its stats, mirroring ``from_kingdom``.

    Returns 4 (last) for non-actions and cards the registry does not know.
    """
    try:
        info = get_card(card)
    except (ValueError, KeyError):
        return 4
    if not info.is_action:
        return 4
    if info.stats.actions >= 2:
        return 0
    if info.stats.actions == 1:
        return 1
    if info.stats.cards >= 2:
        return 2
    return 3


# Commands that register a pending-replay slot when played and fire it on the
# *next* non-Command Action played from hand (Daimyo's ``daimyo_pending``,
# Flagship's ``flagship_pending``). For these, the payload rule that follows the
# Command must stay pinned behind it: the slot has nothing to fire on unless a
# non-Command Action is played after the Command this turn.
#
# Other Commands (Band of Misfits, Captain, Overlord) pick their target from the
# *supply* and resolve immediately on play — they never consume the next hand
# Action, so pinning the following rule behind them would wrongly defeat the
# role-order repair. See ``play_effect`` in ``cards/dark_ages/band_of_misfits.py``
# and ``cards/promo/captain.py`` (both call into the supply) versus
# ``cards/rising_sun/daimyo.py`` and ``cards/plunder/flagship.py`` (both set a
# pending counter consumed in ``game_state`` on the next non-Command Action).
_PENDING_REPLAY_COMMANDS = frozenset({"Daimyo", "Flagship"})

# "Play an Action from hand" multipliers: on play they ask the AI to choose an
# Action *from hand* and replay/multiply it immediately (Throne Room, King's
# Court, Crown in the action phase, Procession), or on their next turn (the
# Mastermind duration). Like pending-replay Commands, the intended payload must
# be played after the multiplier — if the role sort floats a draw/cantrip ahead
# of the multiplier, the payload leaves hand (or is never queued) before the
# multiplier gets to call ``choose_action`` on it, so the multiplier fizzles.
# These select from HAND (unlike supply-targeting Commands), so their following
# non-Command Action payload must stay pinned. See ``play_effect`` /
# ``on_duration`` in ``cards/base_set/throne_room.py``,
# ``cards/prosperity/kings_court.py``, ``cards/empires/crown.py``,
# ``cards/dark_ages/procession.py``, ``cards/plunder/first_mate.py`` and
# ``cards/menagerie/mastermind.py`` (all call ``ai.choose_action`` over the
# hand). The engine exposes no shared structural flag for "replays a chosen
# hand Action", so this mirrors the ``_PENDING_REPLAY_COMMANDS`` named-set
# pattern.
_PLAYS_HAND_ACTION_MULTIPLIERS = frozenset(
    {
        "Throne Room",
        "King's Court",
        "Procession",
        "Crown",
        "Mastermind",
        "First Mate",
    }
)


def _is_command_card(card: str) -> bool:
    """Return True if ``card`` is a registry-known Command (Band of Misfits,
    Captain, Daimyo, Flagship, ...)."""
    try:
        return get_card(card).is_command
    except (ValueError, KeyError):
        return False


def _consumes_next_action(card: str) -> bool:
    """Return True if ``card`` consumes/replays the *next in-hand Action* played
    after it, so its following payload rule must stay pinned behind it.

    Two families qualify and share this rule:

    * Pending-replay Commands (Daimyo, Flagship): register a slot that fires on
      whatever non-Command Action is played next from hand.
    * Play-an-Action multipliers (Throne Room, King's Court, Procession, Crown,
      Mastermind, First Mate): on play (or, for Mastermind, on its next turn)
      they choose an Action *from hand* to replay, so the payload has to still
      be playable after the multiplier rather than floated ahead of it.

    Supply-targeting Commands (Band of Misfits, Captain, Overlord) resolve
    immediately from the supply and are excluded: the rule after them is not a
    payload and must stay free to reflow into role order.
    """
    return card in _PENDING_REPLAY_COMMANDS or card in _PLAYS_HAND_ACTION_MULTIPLIERS


def _normalize_action_priority(strategy: BaseStrategy, info: KingdomInfo) -> None:
    """Repair ungated action rules into safe role order.

    Mutation needs to explore action order, but arbitrary swaps make many
    children obviously dominated, e.g. an unconditional terminal draw above an
    unconditional cantrip. Conditional action rules are left fixed: those are
    the escape hatch for deliberate tactics like "play this terminal first only
    when a specific board state holds."

    Command rules are also left fixed (the role sort treats a Command as a
    terminal and could otherwise sink it). One shared rule covers every card
    that consumes the *next in-hand Action* played after it (see
    ``_consumes_next_action``): pending-replay Commands (Daimyo, Flagship) and
    play-an-Action multipliers (Throne Room, King's Court, Procession, Crown,
    Mastermind, First Mate). For each such rule the first unconditional
    non-Command Action rule after it is pinned too as its payload: the card
    fires on / replays whatever non-Command Action follows it, so seeds
    deliberately emit it before its payload (see
    ``dominion/analysis/seed_genomes.py``); reordering to play the payload first
    would strand the slot (or leave the multiplier nothing to replay) and the
    trick would never fire. Any Command rules sitting between the consuming rule
    and its payload — gated or not — are skipped when choosing the pin target:
    a Command is ``is_command`` regardless of its gate, so it never satisfies a
    pending-replay slot and is not the multiplier's intended hand payload, while
    still being pinned in place on its own iteration.

    Supply-targeting Commands (Band of Misfits, Captain, Overlord) resolve
    immediately from the supply and do *not* consume the next hand Action, so
    the rule after them is not their payload and must stay free to reflow —
    otherwise a board like ``[Band of Misfits, Watchtower, Peddler]`` would
    wrongly keep a terminal pinned ahead of the cantrip.
    """
    action = getattr(strategy, "action_priority", []) or []

    # Pin anchors: gated rules, Command rules, and the unconditional rule
    # directly following a rule that consumes the next in-hand Action (its
    # payload). Pinned rules keep their original slot; only the remaining
    # unconditional rules are role-sorted and reflowed into the gaps between
    # anchors.
    pinned = [False] * len(action)

    def _pin_next_action_payload(idx: int) -> None:
        """Pin the payload of the next-in-hand-Action consumer at ``action[idx]``.

        Both consumer families act on the next *non-Command* Action played from
        hand: a pending-replay Command's slot is only consumed when
        ``choice.is_command`` is false (see ``handle_action_phase``), and a
        play-an-Action multiplier (Throne Room, King's Court, ...) likewise
        replays the Action it picks from hand. Intervening Command rules — gated
        or not — never satisfy the slot and are never the multiplier's intended
        hand payload (a Command is ``is_command`` regardless of its gate), so
        scan past *every* intervening Command rule and pin the first subsequent
        unconditional non-Command Action as the payload. This keeps the true
        payload (e.g. Smithy) ahead of an unrelated cantrip in boards like
        ``[Daimyo, Band of Misfits(gate), Smithy, Peddler]`` and
        ``[Throne Room, Smithy, Peddler]``. Each intervening Command is already
        pinned in its own iteration (and, if itself a consumer, pins its own
        payload), so nested cases like ``[Daimyo, Flagship, Smithy]`` keep every
        rule in place. The scan runs for *gated* consumers too: the gate only
        decides whether the card plays, and when it does it still acts on the
        next non-Command Action, so ``[Daimyo(gate), Smithy, Peddler]`` keeps
        Smithy pinned ahead of Peddler.
        """
        nxt = idx + 1
        while nxt < len(action) and _is_command_card(action[nxt].card_name):
            nxt += 1
        if nxt < len(action) and getattr(action[nxt], "condition", None) is None:
            pinned[nxt] = True

    for idx, rule in enumerate(action):
        gated = getattr(rule, "condition", None) is not None
        is_command = _is_command_card(rule.card_name)
        consumes_next = _consumes_next_action(rule.card_name)
        # Pin the rule in its slot if it is gated, a Command, or a play-an-Action
        # multiplier (which is neither gated nor a Command but must stay ahead of
        # its payload — e.g. Throne Room before Smithy).
        if gated or is_command or consumes_next:
            pinned[idx] = True
        if consumes_next:
            _pin_next_action_payload(idx)

    sorted_movable = iter(
        rule
        for _, rule in sorted(
            (
                (idx, rule)
                for idx, rule in enumerate(action)
                if not pinned[idx]
            ),
            key=lambda pair: (_action_role_rank(pair[1].card_name, info), pair[0]),
        )
    )
    strategy.action_priority = [
        rule if pinned[idx] else next(sorted_movable)
        for idx, rule in enumerate(action)
    ]


def normalize_menu(strategy: BaseStrategy, info: KingdomInfo) -> BaseStrategy:
    """Enforce the invariants every viable menu needs.

    - exactly no duplicate (card, gate) rules — crossover splices can clone;
    - a Province gain rule exists (without one the strategy cannot win);
    - on Colony boards, a Colony gain rule exists;
    - Province/Colony are never shadowed by an *unconditional* basic-treasure
      rule (an uncapped Gold above Province means $8 always buys Gold, so the
      strategy can never green), and Colony is never shadowed by an
      unconditional Province rule (Province matches whenever Colony does, so
      $11+ would always buy Province). Their position relative to gated rules
      stays free — orderings like "first 3 Torturers before greening" are
      legitimate strategy space the GA should explore;
    - never an unconditional Copper/Curse gain rule (pure junk buys);
    - Gold/Silver/Copper (and Platinum, when on the board) present in
      treasure_priority so coins get played.
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
    if info.has_colony and not any(r.card_name == "Colony" for r in strategy.gain_priority):
        strategy.gain_priority.insert(0, PriorityRule("Colony"))

    # Non-shadowing: an unconditional Gold/Silver/Platinum rule above the
    # greening cards would absorb every $6+/$8+ buy forever. Move each
    # greening card directly above the first such rule; gated rules above
    # Province/Colony are left alone (deliberately evolvable ordering).
    gain = strategy.gain_priority
    greens = ["Province"] + (["Colony"] if info.has_colony else [])
    for green in greens:
        shadow_idx = next(
            (i for i, r in enumerate(gain) if r.card_name in _BASIC_TREASURES and r.condition is None),
            None,
        )
        if shadow_idx is None:
            break
        green_idx = next((i for i, r in enumerate(gain) if r.card_name == green), None)
        if green_idx is not None and green_idx > shadow_idx:
            gain.insert(shadow_idx, gain.pop(green_idx))

    # On Colony boards an *unconditional* Province rule above Colony shadows
    # it the same way: Province matches whenever Colony is affordable, so
    # $11+ hands always buy Province. Move the first Colony rule directly
    # above such a Province rule; a gated Province above Colony stays legal.
    if info.has_colony:
        province_idx = next(
            (i for i, r in enumerate(gain) if r.card_name == "Province" and r.condition is None),
            None,
        )
        colony_idx = next((i for i, r in enumerate(gain) if r.card_name == "Colony"), None)
        if province_idx is not None and colony_idx is not None and colony_idx > province_idx:
            gain.insert(province_idx, gain.pop(colony_idx))

    treasure_names = {r.card_name for r in strategy.treasure_priority}
    if info.has_platinum and "Platinum" not in treasure_names:
        strategy.treasure_priority.insert(0, PriorityRule("Platinum"))
    for name in ("Gold", "Silver", "Copper"):
        if name not in treasure_names:
            strategy.treasure_priority.append(PriorityRule(name))

    _normalize_action_priority(strategy, info)

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
