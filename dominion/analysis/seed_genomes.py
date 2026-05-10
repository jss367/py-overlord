"""Seed genomes derived from trick-scanner output.

The genetic evolver in :mod:`evolve` is normally seeded with hand-written
generic engine archetypes (Big Money, Chapel/Witch, Village/Smithy/Lab).
Those templates carry no knowledge of any individual board's mechanical
edge cases, so the evolver has to re-derive every trick on every board
from random mutation. Subtle interactions rarely survive the first
generations because they don't help until the supporting deck is built.

This module bridges that gap. Given a :class:`BoardConfig`, it runs the
:mod:`trick scanner <dominion.analysis.trick_scanner>` and emits one
:class:`EnhancedStrategy` per surfaced interaction, with the trick
pre-encoded into the strategy's gain priority and / or way policy. Each
seed also carries a generic engine baseline (Province, Duchy, Gold,
Silver, Copper) so it is at least playable in isolation. Seeds are
*starting points*: the evolver is expected to mutate them, and bad
tricks should be pruned by selection.

Public API: :func:`build_seed_genomes`.
"""

from __future__ import annotations

from typing import Callable, Optional

from dominion.analysis.trick_scanner import Interaction, scan
from dominion.boards.loader import BoardConfig
from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
    WayRule,
)


# --- Shared baseline ------------------------------------------------------


def _baseline_gain_priority() -> list[PriorityRule]:
    """Generic Province / Duchy / Estate / Gold / Silver fallback rules.

    Trick-specific rules are prepended in front of these so the trick fires
    when affordable; the baseline takes over once the trick is exhausted or
    not affordable on a given turn.
    """

    return [
        PriorityRule("Province"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        PriorityRule("Gold"),
        PriorityRule("Silver", PriorityRule.provinces_left(">", 2)),
    ]


def _baseline_treasure_priority() -> list[PriorityRule]:
    return [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]


def _try_get_card(name: str) -> Optional[Card]:
    try:
        return get_card(name)
    except (KeyError, ValueError):
        return None


def _kingdom_card_objects(board: BoardConfig) -> list[Card]:
    cards: list[Card] = []
    for name in board.kingdom_cards:
        card = _try_get_card(name)
        if card is not None:
            cards.append(card)
    return cards


def _split_card_and_partner(headline: str) -> tuple[str, str]:
    """Pull ``"<Card> + <Way>"`` out of a trash-hook interaction headline.

    The trick scanner formats trash-hook headlines as
    ``"<card> + <way>: ..."`` — see
    :func:`dominion.analysis.trick_scanner.predicate_trash_hook_via_return_to_supply`.
    Parsing the headline keeps this module decoupled from the scanner's
    internal field layout: the only contract is the public ``Interaction``
    dataclass plus this stable headline format.
    """

    head = headline.split(":", 1)[0]
    if "+" not in head:
        return head.strip(), ""
    card_part, way_part = head.split("+", 1)
    return card_part.strip(), way_part.strip()


# --- Builders, one per Interaction.kind -----------------------------------


def _seed_for_trash_hook_unreachable(
    interaction: Interaction, board: BoardConfig
) -> Optional[tuple[str, EnhancedStrategy]]:
    """Seed a strategy that buys ``<card>`` and plays it as the bypassing Way.

    For Flag Bearer + Way of the Butterfly on the Victoria board, this seed
    pays $4 for Flag Bearer (fires its on_gain → take Flag artifact), then
    plays Flag Bearer as Way of the Butterfly (returns it to its pile and
    gains a $5 card without firing on_trash, so the artifact is preserved).
    """

    card_name, way_name = _split_card_and_partner(interaction.headline)
    card = _try_get_card(card_name)
    if card is None or not way_name:
        return None

    strat = EnhancedStrategy()
    strat.name = f"Trick Butterfly {card_name}"
    strat.description = (
        f"Trick-scanner seed: gain {card_name} for its on_gain effect, "
        f"then play it as {way_name} so the on_trash hook is bypassed and "
        f"the +1-cost gain still triggers."
    )

    target_cost = card.cost.coins + 1
    upgrade_targets = sorted(
        {
            c.name
            for c in _kingdom_card_objects(board)
            if c.cost.coins == target_cost and c.cost.potions == card.cost.potions
        }
    )

    gain_rules: list[PriorityRule] = [PriorityRule("Province")]
    # Stock up on the trick card while there's room — three copies is enough
    # to fire the trick a few times per game without flooding the deck.
    gain_rules.append(
        PriorityRule(card_name, PriorityRule.max_in_deck(card_name, 3))
    )
    # Encourage gaining the upgrade targets the Way will hand us, so we
    # actually use them once they're in hand.
    for target in upgrade_targets:
        gain_rules.append(PriorityRule(target))
    gain_rules.extend(_baseline_gain_priority())

    strat.gain_priority = gain_rules
    strat.action_priority = [PriorityRule(card_name)]
    strat.treasure_priority = _baseline_treasure_priority()
    strat.way_policy = [WayRule(card_name=card_name, way_name=way_name)]
    return strat.name, strat


def _seed_for_gain_hook_retriggerable(
    interaction: Interaction, board: BoardConfig
) -> Optional[tuple[str, EnhancedStrategy]]:
    """Seed a strategy that re-buys the on_gain card every chance it gets.

    The trick scanner's headline format here is ``"<card>: on_gain hook
    re-triggerable via <gainer>, <gainer>, ..."`` — see
    :func:`predicate_gain_hook_retriggerable`. We don't try to detect
    artifact loss; we just make the hook card top priority so each fresh
    gain re-fires the artifact / on_gain effect.
    """

    head = interaction.headline.split(":", 1)[0].strip()
    card = _try_get_card(head)
    if card is None:
        return None

    strat = EnhancedStrategy()
    strat.name = f"Trick Re-gain {head}"
    strat.description = (
        f"Trick-scanner seed: keep buying {head} so its on_gain hook "
        f"re-fires (e.g. re-claim its artifact when an opponent holds it)."
    )

    strat.gain_priority = [
        PriorityRule("Province"),
        # Always re-buy the hook card when affordable. We deliberately do
        # *not* gate on "opponent holds the artifact" — most games lack
        # that signal, and the evolver can layer that condition on later.
        PriorityRule(head),
    ] + _baseline_gain_priority()
    strat.action_priority = [PriorityRule(head)]
    strat.treasure_priority = _baseline_treasure_priority()
    return strat.name, strat


def _seed_for_empty_deck_discard_combo(
    interaction: Interaction, board: BoardConfig
) -> Optional[tuple[str, EnhancedStrategy]]:
    """Seed a strategy that thins aggressively and times the empty-deck Event.

    Headline format: ``"<self-exile card> + <event>: ..."``. We bias the
    strategy toward gaining the self-exile card (so the deck/discard
    actually empties) and toward buying the Event whenever it appears as a
    legal purchase. Thinners (Chapel, Donate, Mountebank's curse hand-out)
    are not assumed present; if the kingdom has Chapel or similar trashing
    we don't special-case it here — the evolver can add that.
    """

    card_name, event_name = _split_card_and_partner(interaction.headline)
    if not card_name or not event_name:
        return None
    if _try_get_card(card_name) is None:
        return None

    strat = EnhancedStrategy()
    strat.name = f"Trick Empty-deck {event_name}"
    strat.description = (
        f"Trick-scanner seed: stack {card_name} (sets itself aside on play, "
        f"keeping deck and discard empty) and buy {event_name} whenever "
        f"affordable to cash in the empty-deck payoff."
    )

    strat.gain_priority = [
        PriorityRule("Province"),
        PriorityRule(event_name),
        # Two copies of the self-exile card is enough to trigger the empty
        # condition reliably without choking on a discard pile of dead
        # set-aside cards.
        PriorityRule(card_name, PriorityRule.max_in_deck(card_name, 2)),
    ] + _baseline_gain_priority()
    strat.action_priority = [PriorityRule(card_name)]
    strat.treasure_priority = _baseline_treasure_priority()
    return strat.name, strat


def _seed_for_command_targets(
    interaction: Interaction, board: BoardConfig
) -> Optional[tuple[str, EnhancedStrategy]]:
    """Seed a strategy that pairs the Command card with its top-payload target.

    Headline format: ``"<command>: highest-payload legal Action targets on
    this board"``. The interaction's *detail* string contains the ranked
    target list as ``"... Top legal targets here (by cost + stat payload): A, B, C."``.
    We grab the first listed target and seed a strategy that gains both
    the Command and that target, with an action-priority rule that plays
    the target before the Command (so the Command's replay slot fires it).
    """

    command_name = interaction.headline.split(":", 1)[0].strip()
    if _try_get_card(command_name) is None:
        return None

    detail = interaction.detail
    targets_marker = "targets here (by cost + stat payload):"
    if targets_marker not in detail:
        return None
    listed = detail.split(targets_marker, 1)[1].rstrip(".").strip()
    targets = [t.strip() for t in listed.split(",") if t.strip()]
    if not targets:
        return None
    primary = targets[0]
    if _try_get_card(primary) is None:
        return None

    strat = EnhancedStrategy()
    strat.name = f"Trick {command_name} + {primary}"
    strat.description = (
        f"Trick-scanner seed: pair {command_name} with the kingdom's "
        f"highest-payload legal target ({primary}) so each {command_name} "
        f"play replays / copies a strong terminal."
    )

    strat.gain_priority = [
        PriorityRule("Province"),
        PriorityRule(command_name, PriorityRule.max_in_deck(command_name, 3)),
        PriorityRule(primary, PriorityRule.max_in_deck(primary, 3)),
    ] + _baseline_gain_priority()
    # Play the Command FIRST so its pending-replay slot is registered;
    # then the next non-Command Action played consumes the slot. Reversing
    # this ordering breaks the trick on every "next non-Command Action"
    # Command (Daimyo, Flagship): the payload would be played first and
    # the pending counter set by the Command would have nothing to fire
    # on for the rest of the turn.
    strat.action_priority = [
        PriorityRule(command_name),
        PriorityRule(primary),
    ]
    strat.treasure_priority = _baseline_treasure_priority()
    return strat.name, strat


def _seed_for_cost_mod_gateway(
    interaction: Interaction, board: BoardConfig
) -> Optional[tuple[str, EnhancedStrategy]]:
    """Seed a strategy that stacks the cost reducer and rushes Provinces.

    Headline format: ``"<reducer>: each play reduces every card's cost by
    $1 — opens cheaper gains and chains buys into Provinces"``.
    """

    reducer = interaction.headline.split(":", 1)[0].strip()
    if _try_get_card(reducer) is None:
        return None

    strat = EnhancedStrategy()
    strat.name = f"Trick Cost-mod {reducer}"
    strat.description = (
        f"Trick-scanner seed: stack {reducer} to reduce all card costs by "
        f"$1 per play, opening cheaper gains and chaining Province buys."
    )

    strat.gain_priority = [
        PriorityRule("Province"),
        PriorityRule(reducer, PriorityRule.max_in_deck(reducer, 4)),
    ] + _baseline_gain_priority()
    strat.action_priority = [PriorityRule(reducer)]
    strat.treasure_priority = _baseline_treasure_priority()
    return strat.name, strat


# Dispatch table: kind -> builder.
_BUILDERS: dict[
    str,
    Callable[[Interaction, BoardConfig], Optional[tuple[str, EnhancedStrategy]]],
] = {
    "trash_hook_unreachable": _seed_for_trash_hook_unreachable,
    "gain_hook_retriggerable": _seed_for_gain_hook_retriggerable,
    "empty_deck_discard_combo": _seed_for_empty_deck_discard_combo,
    "command_targets": _seed_for_command_targets,
    "cost_mod_gateway": _seed_for_cost_mod_gateway,
}


def build_seed_genomes(
    board: BoardConfig,
    interactions: Optional[list[Interaction]] = None,
) -> list[tuple[str, EnhancedStrategy]]:
    """Build a list of ``(name, EnhancedStrategy)`` seeds for ``board``.

    If ``interactions`` is omitted, the trick scanner is run against
    ``board`` to discover them. Names within the returned list are unique:
    if two Interactions would yield the same seed name (e.g. two cards
    sharing the same Command target), the duplicate is dropped silently —
    the first wins. Order follows the trick scanner's predicate order, so
    callers iterating the list see related seeds grouped together.
    """

    if interactions is None:
        interactions = scan(board)

    seeds: list[tuple[str, EnhancedStrategy]] = []
    seen_names: set[str] = set()
    for interaction in interactions:
        builder = _BUILDERS.get(interaction.kind)
        if builder is None:
            continue
        result = builder(interaction, board)
        if result is None:
            continue
        name, strategy = result
        if name in seen_names:
            continue
        seen_names.add(name)
        seeds.append((name, strategy))
    return seeds


def trick_signature(strategy: EnhancedStrategy) -> dict[str, list[str]]:
    """Summarise which trick-scanner-shaped patterns a strategy still carries.

    Used by the diversity report in ``evolve.py`` to decide whether an
    evolved descendant *kept* the trick its seed encoded. We deliberately
    look at structural fingerprints rather than identity: the evolver may
    rename, reorder, or wrap rules, but if a way_policy entry routes
    ``<card>`` through a return-to-pile Way, the trash-hook trick is still
    in play.
    """

    return {
        "way_policy": [
            f"{rule.card_name}->{rule.way_name}" for rule in strategy.way_policy
        ],
        "gain_cards": [rule.card for rule in strategy.gain_priority],
        "action_cards": [rule.card for rule in strategy.action_priority],
    }
