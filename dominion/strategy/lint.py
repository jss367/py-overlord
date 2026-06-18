"""Diagnostics for generated and hand-written strategies.

The strategy executor is deliberately simple: it walks ordered priority lists
and picks the first matching card. That makes several mistakes easy to write
and hard to notice from win-rate alone: duplicate rules, unreachable rules
after an unconditional rule for the same card, old ``has_cards(..., 0)``
conditions, and unconditional early greening.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal, Optional

from dominion.boards.loader import BoardConfig
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule, WayRule
from dominion.strategy.card_roles import infer_card_roles
from dominion.strategy.genome_simplification import simplify_strategy

Severity = Literal["info", "warning", "error"]

_HAS_CARDS_ZERO_RE = re.compile(r"^PriorityRule\.has_cards\(.+,\s*0\)$")
_BUILTIN_OFF_MENU_ACTION_GAINS = frozenset({"Trail"})
_GAMESTATE_OFF_MENU_ACTION_GAINERS = frozenset({"Quartermaster"})


@dataclass(frozen=True)
class StrategyLintWarning:
    """A single strategy diagnostic."""

    code: str
    message: str
    list_name: str
    index: int
    card_name: str
    severity: Severity = "warning"


def _condition_source(condition) -> Optional[str]:
    if condition is None:
        return None
    return getattr(condition, "_source", repr(condition))


def _rule_signature(rule: PriorityRule) -> tuple[str, Optional[str]]:
    return rule.card_name, _condition_source(rule.condition)


def _lint_priority_list(
    list_name: str,
    rules: Iterable[PriorityRule],
) -> list[StrategyLintWarning]:
    warnings: list[StrategyLintWarning] = []
    seen_signatures: set[tuple[str, Optional[str]]] = set()
    first_unconditional: dict[str, int] = {}
    seen_province = False

    for idx, rule in enumerate(rules):
        card_name = rule.card_name
        condition_source = _condition_source(rule.condition)

        if condition_source and _HAS_CARDS_ZERO_RE.match(condition_source):
            warnings.append(
                StrategyLintWarning(
                    code="HAS_CARDS_ZERO",
                    message=(
                        "has_cards(..., 0) now means 'has none'; prefer "
                        "has_no_cards(...) for readability."
                    ),
                    list_name=list_name,
                    index=idx,
                    card_name=card_name,
                    severity="info",
                )
            )

        if card_name in first_unconditional:
            warnings.append(
                StrategyLintWarning(
                    code="UNREACHABLE_AFTER_UNCONDITIONAL",
                    message=(
                        f"Earlier unconditional {card_name} rule at index "
                        f"{first_unconditional[card_name]} always wins first."
                    ),
                    list_name=list_name,
                    index=idx,
                    card_name=card_name,
                )
            )

        sig = _rule_signature(rule)
        if sig in seen_signatures:
            warnings.append(
                StrategyLintWarning(
                    code="DUPLICATE_RULE",
                    message="An identical card/condition rule already appears earlier.",
                    list_name=list_name,
                    index=idx,
                    card_name=card_name,
                )
            )
        seen_signatures.add(sig)

        if list_name == "gain":
            if card_name == "Province":
                seen_province = True
            if (
                card_name in {"Duchy", "Estate"}
                and rule.condition is None
                and not seen_province
            ):
                warnings.append(
                    StrategyLintWarning(
                        code="UNCONDITIONAL_GREEN_BEFORE_PROVINCE",
                        message=(
                            f"Unconditional {card_name} appears before any "
                            "Province rule; this often indicates a noisy rush."
                        ),
                        list_name=list_name,
                        index=idx,
                        card_name=card_name,
                    )
                )
            if card_name in {"Copper", "Curse"} and rule.condition is None:
                warnings.append(
                    StrategyLintWarning(
                        code="UNCONDITIONAL_JUNK_GAIN",
                        message=f"Unconditional {card_name} gain is rarely intentional.",
                        list_name=list_name,
                        index=idx,
                        card_name=card_name,
                    )
                )

        if rule.condition is None:
            first_unconditional.setdefault(card_name, idx)

    if list_name == "action":
        warnings.extend(_lint_action_order(list(rules)))

    return warnings


def _lint_action_order(rules: list[PriorityRule]) -> list[StrategyLintWarning]:
    """Flag action-order patterns that are usually tactical mistakes."""

    warnings: list[StrategyLintWarning] = []
    earlier_terminal: tuple[int, PriorityRule] | None = None
    for idx, rule in enumerate(rules):
        roles = infer_card_roles(rule.card_name)
        if roles.has("cantrip") and earlier_terminal is not None:
            earlier_idx, earlier_rule = earlier_terminal
            warnings.append(
                StrategyLintWarning(
                    code="CANTRIP_AFTER_TERMINAL",
                    message=(
                        f"Cantrip {rule.card_name} appears after terminal "
                        f"{earlier_rule.card_name} at index {earlier_idx}; "
                        "cantrips usually preserve actions and should be "
                        "played first unless the terminal is explicitly gated."
                    ),
                    list_name="action",
                    index=idx,
                    card_name=rule.card_name,
                )
            )
            continue

        if (
            roles.has("terminal")
            and not roles.has("nonterminal")
            and rule.condition is None
        ):
            earlier_terminal = (idx, rule)

    return warnings


def _lint_way_policy(rules: Iterable[WayRule]) -> list[StrategyLintWarning]:
    warnings: list[StrategyLintWarning] = []
    seen_signatures: set[tuple[str, str, Optional[str]]] = set()
    first_unconditional: dict[tuple[str, str], int] = {}

    for idx, rule in enumerate(rules):
        source = _condition_source(rule.condition)
        pair = (rule.card_name, rule.way_name)
        sig = (rule.card_name, rule.way_name, source)

        if pair in first_unconditional:
            warnings.append(
                StrategyLintWarning(
                    code="UNREACHABLE_WAY_AFTER_UNCONDITIONAL",
                    message=(
                        f"Earlier unconditional {rule.card_name} -> {rule.way_name} "
                        f"rule at index {first_unconditional[pair]} always wins first."
                    ),
                    list_name="way_policy",
                    index=idx,
                    card_name=rule.card_name,
                )
            )
        if sig in seen_signatures:
            warnings.append(
                StrategyLintWarning(
                    code="DUPLICATE_WAY_RULE",
                    message="An identical card/way/condition rule already appears earlier.",
                    list_name="way_policy",
                    index=idx,
                    card_name=rule.card_name,
                )
            )
        seen_signatures.add(sig)
        if rule.condition is None:
            first_unconditional.setdefault(pair, idx)

    return warnings


def lint_strategy(strategy: EnhancedStrategy) -> list[StrategyLintWarning]:
    """Return diagnostics for the strategy without mutating it."""

    warnings: list[StrategyLintWarning] = []
    for list_name, rules in (
        ("gain", getattr(strategy, "gain_priority", []) or []),
        ("action", getattr(strategy, "action_priority", []) or []),
        ("treasure", getattr(strategy, "treasure_priority", []) or []),
        ("trash", getattr(strategy, "trash_priority", []) or []),
    ):
        warnings.extend(_lint_priority_list(list_name, rules))

    warnings.extend(_lint_way_policy(getattr(strategy, "way_policy", []) or []))
    return warnings


def normalize_strategy(strategy: EnhancedStrategy) -> EnhancedStrategy:
    """Return a behavior-preserving simplified copy of ``strategy``."""

    return simplify_strategy(strategy)


def _board_has_non_card_off_menu_gain_paths(board_config: BoardConfig | None) -> bool:
    if board_config is None:
        return True
    return bool(
        board_config.events
        or board_config.ways
        or board_config.allies
        or board_config.traits
    )


def _card_can_gain_off_menu_actions(card_name: str) -> bool:
    return (
        card_name == "Collection"
        or card_name in _GAMESTATE_OFF_MENU_ACTION_GAINERS
        or infer_card_roles(card_name).has("gainer")
    )


def cleanup_for_publication(
    strategy: EnhancedStrategy,
    *,
    board_config: BoardConfig | None = None,
) -> EnhancedStrategy:
    """Return a generated-strategy copy suitable for publication.

    This pass is intentionally conservative. It keeps the evaluated gain policy
    intact, applies behavior-preserving syntactic simplification, and removes
    action rules for cards the strategy never tries to gain only when the board
    context rules out off-menu Action gain paths. Collection, gainers, Events,
    Ways, Allies, and Traits can cause a strategy to gain Actions that are not
    explicitly named in gain_priority, so action priorities remain meaningful
    in those cases.
    """

    cleaned = normalize_strategy(strategy)
    gained_cards = {rule.card_name for rule in getattr(cleaned, "gain_priority", []) or []}
    can_gain_off_menu_actions = _board_has_non_card_off_menu_gain_paths(board_config) or any(
        _card_can_gain_off_menu_actions(card_name) for card_name in gained_cards
    )
    if gained_cards and not can_gain_off_menu_actions:
        cleaned.action_priority = [
            rule
            for rule in getattr(cleaned, "action_priority", []) or []
            if (
                rule.card_name in gained_cards
                or rule.card_name in _BUILTIN_OFF_MENU_ACTION_GAINS
            )
        ]
    return cleaned
