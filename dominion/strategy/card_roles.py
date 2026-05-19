"""Lightweight card-role inference for strategy planning.

These roles are intentionally heuristic. They give phase-aware strategies and
seed builders a shared vocabulary ("village", "terminal_draw", "payload",
"gainer", etc.) without requiring every card implementation to maintain a
manual metadata table.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import lru_cache

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card


@dataclass(frozen=True)
class CardRoleProfile:
    name: str
    roles: frozenset[str]

    def has(self, role: str) -> bool:
        return role in self.roles


def _class_source(card: Card) -> str:
    try:
        return inspect.getsource(type(card))
    except (OSError, TypeError):
        return ""


@lru_cache(maxsize=None)
def infer_card_roles(card_name: str) -> CardRoleProfile:
    """Infer broad strategic roles for a card name."""

    card = get_card(card_name)
    roles: set[str] = set()
    source = _class_source(card)

    if card.is_action:
        roles.add("action")
        if card.stats.actions > 0:
            roles.add("nonterminal")
            roles.add("village")
        else:
            roles.add("terminal")
        if card.stats.cards >= 1 and card.stats.actions >= 1:
            roles.add("cantrip")
        if card.stats.cards >= 2:
            roles.add("draw")
        if card.stats.cards >= 2 and card.stats.actions == 0:
            roles.add("terminal_draw")
        if card.stats.coins >= 2 or card.stats.buys > 0:
            roles.add("payload")
        if card.is_attack:
            roles.add("attack")
        if card.is_duration:
            roles.add("duration")
        if card.is_command:
            roles.add("command")

    if card.is_treasure:
        roles.add("treasure")
        if card.stats.coins >= 2:
            roles.add("payload")

    if card.is_victory:
        roles.add("victory")

    lowered = source.lower()
    if "trash" in lowered:
        roles.add("trasher")
    if "gain_card(" in source:
        roles.add("gainer")
    if "discard" in lowered and card.is_action:
        roles.add("sifter")
    if "choose_" in source or "should_" in source:
        roles.add("mode_or_choice")

    return CardRoleProfile(card.name, frozenset(roles))


def cards_with_role(card_names: list[str], role: str) -> list[str]:
    """Return the subset of ``card_names`` inferred to have ``role``."""

    matched: list[str] = []
    for card_name in card_names:
        try:
            if infer_card_roles(card_name).has(role):
                matched.append(card_name)
        except (KeyError, ValueError):
            continue
    return matched
