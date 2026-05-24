"""Trick scanner: surface non-obvious card x Way/Event/Artifact interactions per kingdom.

Strong Dominion play on a given board often hinges on a single mechanical edge case
(e.g. ``Way of the Butterfly`` returns the played card to its supply pile rather than
trashing it, so ``Flag Bearer``'s on_trash artifact-grab does not fire, leaving you with
a $4-to-gain-a-$5 plus a permanent +1 Card / turn). These tricks are mechanical facts
visible in source but invisible if you reason about cards from their English text.

This module walks a board's registered cards, Ways and Events and emits hypotheses
based on a small set of interaction predicates. Each predicate is a pure function
``(BoardConfig) -> list[Interaction]`` that can be tested in isolation.

CLI::

    python -m dominion.analysis.trick_scanner --board boards/<file>.txt
"""

from __future__ import annotations

import argparse
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from dominion.boards.loader import BoardConfig, load_board
from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.ways.registry import get_way


# --- Knowledge tables -----------------------------------------------------
#
# Small, explicit tables of mechanical facts that can't be derived by simple
# class inspection. Keep these focused — anything that *can* be derived from a
# class (overridden hooks, `gain_card` calls in source) is detected
# heuristically below.

# Ways that return the played card to its supply pile rather than trashing it.
# These are the Ways that bypass on_trash hooks.
RETURN_TO_PILE_WAYS = frozenset({"Way of the Butterfly"})

# Cards that, when played, exile or set aside themselves so they live outside
# the player's deck and discard. Relevant for events that key on an empty deck
# *and* empty discard.
#
# Native Village is intentionally NOT here: its play_effect sets aside the
# *top of the deck* onto the Native Village mat, while Native Village itself
# stays in play and goes to discard at clean-up. Adding it would emit a
# hypothesis for a state that cannot occur.
SELF_EXILE_OR_SET_ASIDE_CARDS = frozenset({"Stockpile", "Island"})

# Events that key on the player having an empty deck *and* empty discard.
EMPTY_DECK_DISCARD_EVENTS = frozenset({"Windfall"})


# Per-Command-card target filters. Each entry takes a candidate Card and
# returns True iff this Command card can legally play / replay / copy it.
# Commands whose only filter is "non-Command Action" use the default below.
_DEFAULT_COMMAND_FILTER: Callable[["Card"], bool] = (
    lambda c: c.is_action and not c.is_command
)
COMMAND_TARGET_FILTERS: dict[str, Callable[["Card"], bool]] = {
    # Captain (promo): plays a non-Command non-Duration Action from supply
    # costing up to $4, with no potion / debt cost.
    "Captain": lambda c: (
        c.is_action
        and not c.is_command
        and not c.is_duration
        and c.cost.coins <= 4
        and c.cost.potions == 0
        and c.cost.debt == 0
    ),
    # Band of Misfits: plays a non-Command Action from supply costing strictly
    # less than its own $5 *by printed cost*, with no potion / debt cost. The
    # in-game implementation uses dynamic cost via get_card_cost(), so symmetric
    # cost reducers (Bridge, Highway, Quarry on Actions, ...) do not change
    # legality (both costs drop by the same amount). Pile-specific reducers
    # (Family of Inventors -$1 tokens, Ferry -$2 token, Plunder "Cheap" trait)
    # can unlock additional same-printed-cost targets at runtime; the static
    # scanner can't see those without simulating the game.
    "Band of Misfits": lambda c: (
        c.is_action
        and not c.is_command
        and c.cost.coins < 5
        and c.cost.potions == 0
        and c.cost.debt == 0
    ),
    # Flagship: replays the next non-Command Action played this turn. The
    # engine (game_state.py: pending_flagships consumed when a non-Command is
    # played) does NOT exclude Durations — pairing Flagship with Wharf or
    # other strong Durations is legal and a known interaction.
    "Flagship": lambda c: c.is_action and not c.is_command,
}


# --- Public types --------------------------------------------------------


@dataclass(slots=True)
class Interaction:
    """A single hypothesis surfaced by a predicate."""

    kind: str
    headline: str
    detail: str = ""
    refs: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"- **{self.headline}**"]
        if self.detail:
            lines.append(f"  - {self.detail}")
        for ref in self.refs:
            if ref:
                lines.append(f"  - `{ref}`")
        return "\n".join(lines)


# --- Helpers --------------------------------------------------------------


def _source_ref(cls_or_obj) -> str:
    """Return a ``path:line`` source reference for a class or instance."""

    cls = cls_or_obj if inspect.isclass(cls_or_obj) else type(cls_or_obj)
    try:
        path = inspect.getsourcefile(cls) or ""
        _, line = inspect.getsourcelines(cls)
    except (TypeError, OSError):
        return ""
    return f"{path}:{line}"


def _has_method_override(card: Card, name: str) -> bool:
    """True iff ``card``'s class (or an intermediate base) overrides ``Card.<name>``."""

    base = getattr(Card, name)
    method = getattr(type(card), name, None)
    return method is not None and method is not base


def _kingdom_card_objects(board: BoardConfig) -> list[Card]:
    cards: list[Card] = []
    for name in board.kingdom_cards:
        try:
            cards.append(get_card(name))
        except (KeyError, ValueError):
            continue
    return cards


def _class_source(card: Card) -> str:
    try:
        return inspect.getsource(type(card))
    except (TypeError, OSError):
        return ""


# --- Predicates ----------------------------------------------------------


def predicate_trash_hook_via_return_to_supply(board: BoardConfig) -> list[Interaction]:
    """Predicate 1 — Trash hook unreachable via return-to-supply Way.

    For every kingdom card with a non-trivial ``on_trash`` hook, check whether any
    in-kingdom Way returns the played card to its supply pile. If so, the Way bypasses
    the on_trash hook entirely.
    """

    return_ways = [w for w in board.ways if w in RETURN_TO_PILE_WAYS]
    if not return_ways:
        return []

    interactions: list[Interaction] = []
    for card in _kingdom_card_objects(board):
        # Ways are applied in place of an Action's normal play, so only Action
        # cards can be routed through a Way at all.
        if not card.is_action:
            continue
        if not _has_method_override(card, "on_trash"):
            continue
        for way_name in return_ways:
            try:
                way = get_way(way_name)
            except (KeyError, ValueError):
                continue
            interactions.append(
                Interaction(
                    kind="trash_hook_unreachable",
                    headline=(
                        f"{card.name} + {way_name}: on_trash hook unreachable when "
                        f"returned to pile"
                    ),
                    detail=(
                        f"{card.name} has an on_trash effect, but {way_name} returns "
                        f"the played card to its supply pile rather than trashing it. "
                        f"Playing {card.name} as {way_name} preserves anything the "
                        f"on_trash hook hands you (artifact, token, etc.) while still "
                        f"gaining a card costing $1 more."
                    ),
                    refs=[_source_ref(card), _source_ref(way)],
                )
            )
    return interactions


def predicate_gain_hook_retriggerable(board: BoardConfig) -> list[Interaction]:
    """Predicate 2 — Gain hook re-triggerable.

    For every kingdom card with an ``on_gain`` override, list other in-kingdom
    effects that gain cards from the supply (Workshop-likes, Duplicate, Way of the
    Butterfly, etc.). Each fresh gain re-fires the on_gain hook.
    """

    gainer_names: list[str] = []
    for card in _kingdom_card_objects(board):
        src = _class_source(card)
        if "gain_card(" in src:
            gainer_names.append(card.name)
    if "Way of the Butterfly" in board.ways:
        gainer_names.append("Way of the Butterfly")
    if not gainer_names:
        return []

    interactions: list[Interaction] = []
    for card in _kingdom_card_objects(board):
        if not _has_method_override(card, "on_gain"):
            continue
        sources_for_card = [g for g in gainer_names if g != card.name]
        if not sources_for_card:
            continue
        joined = ", ".join(sources_for_card)
        interactions.append(
            Interaction(
                kind="gain_hook_retriggerable",
                headline=(
                    f"{card.name}: on_gain hook re-triggerable via {joined}"
                ),
                detail=(
                    f"{card.name} has a custom on_gain effect, and this kingdom "
                    f"contains effects that gain cards from the supply ({joined}). "
                    f"Each gainer that can target {card.name} fires its on_gain "
                    f"hook again — verify the gainer's cost / type filter actually "
                    f"reaches {card.name}."
                ),
                refs=[_source_ref(card)],
            )
        )
    return interactions


def predicate_empty_deck_discard_triggers(board: BoardConfig) -> list[Interaction]:
    """Predicate 3 — Empty-deck/discard triggers.

    Events such as ``Windfall`` only pay out when both the player's deck and discard
    are empty. Cards that exile or set aside themselves on play (Stockpile, Island,
    Native Village) make that condition reachable on demand.
    """

    events_present = [e for e in board.events if e in EMPTY_DECK_DISCARD_EVENTS]
    if not events_present:
        return []
    self_exile = [c for c in board.kingdom_cards if c in SELF_EXILE_OR_SET_ASIDE_CARDS]
    if not self_exile:
        return []

    interactions: list[Interaction] = []
    for event_name in events_present:
        try:
            event = get_event(event_name)
        except (KeyError, ValueError):
            continue
        for card_name in self_exile:
            try:
                card = get_card(card_name)
            except (KeyError, ValueError):
                continue
            interactions.append(
                Interaction(
                    kind="empty_deck_discard_combo",
                    headline=(
                        f"{card_name} + {event_name}: set-aside cards keep deck "
                        f"and discard empty for {event_name}'s payoff"
                    ),
                    detail=(
                        f"{card_name} sets itself aside or exiles itself on play, "
                        f"so it does not occupy the deck or discard. Together with "
                        f"Treasures that exit play this turn, that makes "
                        f"{event_name}'s empty-deck-and-discard condition reachable "
                        f"on demand."
                    ),
                    refs=[_source_ref(card), _source_ref(event)],
                )
            )
    return interactions


def predicate_command_targets(board: BoardConfig) -> list[Interaction]:
    """Predicate 4 — Command targets.

    For every Command card on this board (Daimyo, Royal Carriage, Captain, ...),
    enumerate the highest-payload Action targets it can *legally* play / replay
    on this board. Each Command's per-card filter (cost cap, type restrictions)
    lives in :data:`COMMAND_TARGET_FILTERS`; cards without an explicit filter use
    the default ``non-Command Action`` rule.
    """

    cards = _kingdom_card_objects(board)
    commands = [c for c in cards if c.is_command]
    if not commands:
        return []

    def _payload(c: Card) -> tuple[int, int, str]:
        # Rough heuristic: rank by cost first, then by a weighted stat sum.
        stat_sum = (
            c.stats.cards * 2
            + c.stats.actions
            + c.stats.coins * 2
            + c.stats.buys
            + c.stats.vp * 2
        )
        return (c.cost.coins + c.cost.debt, stat_sum, c.name)

    interactions: list[Interaction] = []
    for command in commands:
        target_filter = COMMAND_TARGET_FILTERS.get(
            command.name, _DEFAULT_COMMAND_FILTER
        )
        candidates = [c for c in cards if c.name != command.name and target_filter(c)]
        if not candidates:
            continue
        ranked = sorted(candidates, key=_payload, reverse=True)
        top_targets = [c.name for c in ranked[:5]]
        interactions.append(
            Interaction(
                kind="command_targets",
                headline=(
                    f"{command.name}: highest-payload legal Action targets on this board"
                ),
                detail=(
                    f"{command.name} replays / copies an Action it is allowed to "
                    f"target. Top legal targets here (by cost + stat payload): "
                    f"{', '.join(top_targets)}."
                ),
                refs=[_source_ref(command)],
            )
        )
    return interactions


def predicate_cost_mod_gateways(board: BoardConfig) -> list[Interaction]:
    """Predicate 5 — Cost-mod gateways.

    For every cost-modifying card in the kingdom (detected by an assignment to
    ``player.cost_reduction`` in the card's source), summarise which kingdom and
    Province-tier piles drop into reach with each play.
    """

    cards = _kingdom_card_objects(board)
    mods: list[Card] = []
    for card in cards:
        src = _class_source(card)
        if "cost_reduction" in src and "+=" in src:
            mods.append(card)
    if not mods:
        return []

    breakpoints: dict[int, list[str]] = {}
    for c in cards:
        if c.cost.coins <= 0:
            continue
        breakpoints.setdefault(c.cost.coins, []).append(c.name)
    summary_parts = [
        f"${orig} → ${orig - 1}: {', '.join(sorted(names))}"
        for orig, names in sorted(breakpoints.items())
    ]
    # Province sits outside the kingdom but is the headline target.
    province_summary = "$8 → $7 (Province) with one play; $6 with two."

    interactions: list[Interaction] = []
    for mod in mods:
        interactions.append(
            Interaction(
                kind="cost_mod_gateway",
                headline=(
                    f"{mod.name}: each play reduces every card's cost by $1 — "
                    f"opens cheaper gains and chains buys into Provinces"
                ),
                detail="; ".join(summary_parts + [province_summary]),
                refs=[_source_ref(mod)],
            )
        )
    return interactions


PREDICATES = (
    predicate_trash_hook_via_return_to_supply,
    predicate_gain_hook_retriggerable,
    predicate_empty_deck_discard_triggers,
    predicate_command_targets,
    predicate_cost_mod_gateways,
)


def scan(board: BoardConfig) -> list[Interaction]:
    """Run every predicate against ``board`` and return all surfaced interactions."""

    interactions: list[Interaction] = []
    for predicate in PREDICATES:
        interactions.extend(predicate(board))
    return interactions


def render_markdown(
    board_path: Path | str,
    board: BoardConfig,
    interactions: Iterable[Interaction],
) -> str:
    """Render a markdown report for ``board`` and ``interactions``."""

    lines = [f"# Trick scan: `{board_path}`", ""]
    if board.kingdom_cards:
        lines.append(f"**Kingdom**: {', '.join(board.kingdom_cards)}  ")
    landscape_bits: list[str] = []
    if board.events:
        landscape_bits.append(f"Events: {', '.join(board.events)}")
    if board.ways:
        landscape_bits.append(f"Ways: {', '.join(board.ways)}")
    if board.projects:
        landscape_bits.append(f"Projects: {', '.join(board.projects)}")
    if board.landmarks:
        landscape_bits.append(f"Landmarks: {', '.join(board.landmarks)}")
    if board.allies:
        landscape_bits.append(f"Allies: {', '.join(board.allies)}")
    if landscape_bits:
        lines.append(" | ".join(landscape_bits))
    lines.append("")

    interactions = list(interactions)
    if not interactions:
        lines.append("_No interactions surfaced._")
    else:
        lines.append(f"## {len(interactions)} hypothesis interaction(s)")
        lines.append("")
        for interaction in interactions:
            lines.append(interaction.to_markdown())
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Surface non-obvious card x landscape interactions for a Dominion kingdom."
        )
    )
    parser.add_argument(
        "--board",
        required=True,
        help="Path to a board definition file (e.g. boards/victoria_kingdom.txt).",
    )
    args = parser.parse_args(argv)

    board_path = Path(args.board)
    board = load_board(board_path)
    interactions = scan(board)
    print(render_markdown(board_path, board, interactions))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
