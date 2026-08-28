"""Board-derived engine archetype seeds.

The trick scanner surfaces narrow mechanical interactions, and the reuse
library recalls proven strategies — but neither *composes* an engine. On
the Oslo board the winning strategy was a Workers' Village / Magnate /
Bank / King's Court engine no automatic seed ever assembled: each piece
alone loses to money, so the GA discarded every partial version (a
fitness valley), and the winning composition was only found after a
human supplied the topology.

This module makes that topology a searchable starting point. Engines are
a slot-filling problem over :mod:`card capabilities
<dominion.analysis.card_capabilities>`:

- a **village** (2+ actions) and a **draw** source (2+ expected cards)
  form the core — without both, no engine, no seeds;
- **payload** (2+ coins per play), a **multiplier** (Throne Room family),
  a cheap **gainer**, and a **+buy** source attach as support when the
  kingdom offers them.

Each role-complete combination becomes one complete
:class:`EnhancedStrategy` seed with *aggressive* component counts
(seven-ish core copies, not the conservative caps random init uses):
trimming an overbuilt engine is an easy sequence of GA mutations, while
assembling one from a money deck is the fitness valley that motivated
this module. Seeds delay greening until the engine draws, and balance
core gains via a deck-count-difference gate.

Public API: :func:`build_engine_seeds`.
"""

from __future__ import annotations

from dataclasses import dataclass

from dominion.analysis.card_capabilities import (
    CardCapabilities,
    kingdom_capabilities,
)
from dominion.boards.loader import BoardConfig
from dominion.simulation.structured_genome import BASIC_CARDS
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

# Core-copy cap: enough for a dominant engine (the Oslo winner ran seven
# Workers' Villages and seven Magnates); the GA trims from here.
_CORE_CAP = 7
_SUPPORT_CAP = 2
_MULTIPLIER_CAP = 3

# Treasures whose coin value counts other cards already in play (Bank).
# They only reach full value played after every other Treasure.
_PLAY_LAST_TREASURES = frozenset({"Bank", "Fortune"})


@dataclass(frozen=True)
class EngineParts:
    """One role-complete engine composition for a kingdom."""

    village: CardCapabilities
    draw: CardCapabilities
    payloads: tuple[CardCapabilities, ...]
    multiplier: CardCapabilities | None
    gainer: CardCapabilities | None
    buy_source: CardCapabilities | None

    @property
    def dual_core(self) -> bool:
        """True when one card fills both the village and draw slots."""
        return self.village.name == self.draw.name

    @property
    def name(self) -> str:
        if self.dual_core:
            return f"Engine {self.village.name}"
        return f"Engine {self.village.name} + {self.draw.name}"

    def chosen(self) -> list[CardCapabilities]:
        parts = [self.village]
        if not self.dual_core:
            parts.append(self.draw)
        parts.extend(self.payloads)
        for extra in (self.multiplier, self.gainer, self.buy_source):
            if extra is not None:
                parts.append(extra)
        return parts


def enumerate_engine_parts(
    board: BoardConfig, max_engines: int = 3
) -> list[EngineParts]:
    """Enumerate the strongest role-complete engine compositions.

    Returns at most ``max_engines`` compositions, best core first, or an
    empty list when the kingdom lacks a village or a draw source.
    """

    caps = {
        name: c
        for name, c in kingdom_capabilities(board.kingdom_cards).items()
        if name not in BASIC_CARDS
    }

    villages = [c for c in caps.values() if c.is_action and c.actions >= 2]
    draws = [c for c in caps.values() if c.is_action and c.draw >= 2]

    cores: list[tuple[float, CardCapabilities, CardCapabilities]] = []
    for village in villages:
        for draw in draws:
            if village.name == draw.name and not (
                village.actions >= 2 and village.draw >= 2
            ):
                continue
            score = (
                draw.draw * 2.0
                + village.actions
                + (village.buys + draw.buys) * 0.5
                + (village.draw + draw.coins) * 0.25
            )
            cores.append((score, village, draw))
    cores.sort(key=lambda c: (-c[0], c[1].name, c[2].name))

    engines: list[EngineParts] = []
    for _score, village, draw in cores[:max_engines]:
        core_names = {village.name, draw.name}

        payloads = sorted(
            (
                c
                for c in caps.values()
                if c.name not in core_names and c.coins >= 2
            ),
            key=lambda c: (-c.coins, -c.buys, -c.cost, c.name),
        )[:2]
        chosen_names = core_names | {c.name for c in payloads}

        multipliers = sorted(
            (
                c
                for c in caps.values()
                if c.is_multiplier and c.name not in chosen_names
            ),
            key=lambda c: (-c.cost, c.name),
        )
        multiplier = multipliers[0] if multipliers else None
        if multiplier:
            chosen_names.add(multiplier.name)

        # Support gainers accelerate assembly; prefer the cheapest so it
        # slots under the engine's own buys.
        gainers = sorted(
            (
                c
                for c in caps.values()
                if c.is_gainer and c.name not in chosen_names
            ),
            key=lambda c: (c.cost, c.name),
        )
        gainer = gainers[0] if gainers else None
        if gainer:
            chosen_names.add(gainer.name)

        buy_source = None
        if not any(caps[name].buys >= 1 for name in chosen_names):
            buy_options = sorted(
                (
                    c
                    for c in caps.values()
                    if c.buys >= 1 and c.name not in chosen_names
                ),
                key=lambda c: (c.cost, c.name),
            )
            buy_source = buy_options[0] if buy_options else None

        engines.append(
            EngineParts(
                village=village,
                draw=draw,
                payloads=tuple(payloads),
                multiplier=multiplier,
                gainer=gainer,
                buy_source=buy_source,
            )
        )
    return engines


def _gain_priority(parts: EngineParts, board: BoardConfig) -> list[PriorityRule]:
    village, draw = parts.village, parts.draw
    has_colony = "Colony" in board.kingdom_cards
    has_platinum = "Platinum" in board.kingdom_cards

    rules: list[PriorityRule] = []

    # A cheap gainer bought as the opening turns' first gain accelerates
    # assembly for the rest of the game (the Oslo winner opens on Anvils).
    cheap_gainer = parts.gainer is not None and parts.gainer.cost <= 4
    if parts.gainer is not None and cheap_gainer:
        rules.append(
            PriorityRule(
                parts.gainer.name,
                PriorityRule.and_(
                    PriorityRule.max_in_deck(parts.gainer.name, _SUPPORT_CAP),
                    PriorityRule.cards_gained_this_turn("==", 0),
                    PriorityRule.turn_number("<=", 7),
                ),
            )
        )

    if has_colony:
        rules.append(PriorityRule("Colony"))
        # Delay Provinces until the Colony race is decided or time runs out
        # — greening early is how half-built engines lose to money.
        rules.append(
            PriorityRule(
                "Province",
                PriorityRule.or_(
                    PriorityRule.colonies_left("<=", 2),
                    PriorityRule.turn_number(">=", 18),
                ),
            )
        )
    else:
        rules.append(
            PriorityRule(
                "Province",
                PriorityRule.or_(
                    PriorityRule.has_cards([draw.name], 2),
                    PriorityRule.turn_number(">=", 14),
                ),
            )
        )
    rules.append(PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)))

    # Payload outranks the core: with a big-money hand mid-build, a Bank or
    # Grand Market converts it now, while another core copy only helps later.
    for payload in sorted(parts.payloads, key=lambda c: (-c.cost, c.name)):
        rules.append(
            PriorityRule(payload.name, PriorityRule.max_in_deck(payload.name, _SUPPORT_CAP))
        )

    if parts.multiplier is not None:
        # A multiplier is dead weight until there is something worth
        # tripling — wait for a critical mass of the draw component.
        rules.append(
            PriorityRule(
                parts.multiplier.name,
                PriorityRule.and_(
                    PriorityRule.max_in_deck(parts.multiplier.name, _MULTIPLIER_CAP),
                    PriorityRule.has_cards([draw.name], 3),
                ),
            )
        )

    if has_platinum:
        rules.append(PriorityRule("Platinum", PriorityRule.max_in_deck("Platinum", 1)))

    if parts.dual_core:
        rules.append(
            PriorityRule(village.name, PriorityRule.max_in_deck(village.name, _CORE_CAP + 1))
        )
    else:
        # Keep the core balanced: never let the draw component run more
        # than one copy ahead of the village component.
        rules.append(
            PriorityRule(
                draw.name,
                PriorityRule.and_(
                    PriorityRule.max_in_deck(draw.name, _CORE_CAP),
                    PriorityRule.deck_count_diff(draw.name, village.name, "<=", 1),
                ),
            )
        )
        rules.append(
            PriorityRule(village.name, PriorityRule.max_in_deck(village.name, _CORE_CAP))
        )

    supports = [parts.buy_source]
    if not cheap_gainer:
        supports.append(parts.gainer)
    for support in supports:
        if support is not None:
            rules.append(
                PriorityRule(support.name, PriorityRule.max_in_deck(support.name, _SUPPORT_CAP))
            )

    rules.append(PriorityRule("Estate", PriorityRule.provinces_left("<=", 1)))
    # Economy fallback stays ungated: a starving engine deck is worse than a
    # slightly diluted one, and the GA can tighten these later.
    rules.append(PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 2)))
    rules.append(PriorityRule("Silver"))
    return rules


def _action_priority(parts: EngineParts) -> list[PriorityRule]:
    actions = [c for c in parts.chosen() if c.is_action]
    # Villages and cantrips first (they never waste the action), then the
    # multiplier (so its replay slot targets what follows), then draw,
    # then the remaining terminals.
    def rank(c: CardCapabilities) -> tuple:
        if c.actions >= 2:
            tier = 0
        elif c.actions == 1 and not c.is_multiplier:
            tier = 1
        elif c.is_multiplier:
            tier = 2
        elif c.draw >= 2:
            tier = 3
        else:
            tier = 4
        return (tier, -c.cost, c.name)

    return [PriorityRule(c.name) for c in sorted(actions, key=rank)]


def _treasure_priority(parts: EngineParts, board: BoardConfig) -> list[PriorityRule]:
    rules: list[PriorityRule] = []
    if "Platinum" in board.kingdom_cards:
        rules.append(PriorityRule("Platinum"))
    rules.append(PriorityRule("Gold"))
    kingdom_treasures = [c for c in parts.chosen() if c.is_treasure]
    for c in sorted(kingdom_treasures, key=lambda c: (-c.coins, c.name)):
        if c.name not in _PLAY_LAST_TREASURES:
            rules.append(PriorityRule(c.name))
    rules.append(PriorityRule("Silver"))
    rules.append(PriorityRule("Copper"))
    for c in kingdom_treasures:
        if c.name in _PLAY_LAST_TREASURES:
            rules.append(PriorityRule(c.name))
    return rules


def build_engine_seeds(
    board: BoardConfig, max_engines: int = 3
) -> list[tuple[str, EnhancedStrategy]]:
    """Build ``(name, EnhancedStrategy)`` engine seeds for ``board``.

    Names are unique within the returned list (compositions are keyed by
    their core pair). Boards without a viable core return an empty list.
    """

    seeds: list[tuple[str, EnhancedStrategy]] = []
    for parts in enumerate_engine_parts(board, max_engines=max_engines):
        strat = EnhancedStrategy()
        strat.name = parts.name
        support = ", ".join(c.name for c in parts.chosen()[2 if not parts.dual_core else 1 :])
        strat.description = (
            f"Board-derived engine archetype: {parts.village.name} for actions, "
            f"{parts.draw.name} for draw"
            + (f", supported by {support}" if support else "")
            + ". Seeded fully assembled with aggressive core counts; "
            "the evolver trims and re-times it."
        )
        strat.gain_priority = _gain_priority(parts, board)
        strat.action_priority = _action_priority(parts)
        strat.treasure_priority = _treasure_priority(parts, board)
        seeds.append((strat.name, strat))
    return seeds
