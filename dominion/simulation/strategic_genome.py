"""Typed, phase-aware genome for Dominion strategy search.

The original structured genome mutates a compiled priority list directly.
That keeps random strategies coherent, but it loses the strategic meaning of
an edit: "move this rule" can accidentally change an opening, a greening
threshold, or an endgame tactic.  This module stores those concepts as typed
blocks and compiles them to the existing :class:`BaseStrategy` phenotype.

Keeping the phenotype unchanged is deliberate.  Battles, decision tracing,
linting, generated Python strategies, and hand-written seed strategies all
continue to use ordinary ``PriorityRule`` lists.  The trainer can use semantic
mutation/crossover whenever both parents carry ``_strategic_genome`` and fall
back to the legacy structured operators for older seeds.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import random as _random_module
import re
from typing import Literal

from dominion.strategy.card_roles import infer_card_roles
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


@dataclass
class OpeningTarget:
    """Buy exactly ``copies`` of ``card`` during the opening window."""

    card: str
    copies: int = 1
    through_turn: int = 4


@dataclass
class BuildTarget:
    """A deck-composition target used during the build phase."""

    card: str
    copies: int
    from_turn: int | None = None
    through_turn: int | None = None
    while_provinces_above: int | None = None
    requires_card: str | None = None
    priority_band: Literal[
        "before_province",
        "before_duchy",
        "build",
        "before_silver",
        "fallback",
    ] = "build"

    def normalize_timing(self) -> None:
        """Keep independently mutated phase bounds as a reachable window."""

        if (
            self.from_turn is not None
            and self.through_turn is not None
            and self.from_turn > self.through_turn
        ):
            self.from_turn, self.through_turn = self.through_turn, self.from_turn


@dataclass
class EconomyPlan:
    buy_gold: bool = True
    buy_silver: bool = True
    silver_cap: int | None = None
    silver_through_turn: int | None = None
    gold_cap: int | None = None
    prefer_platinum: bool = True


@dataclass
class GreeningPlan:
    """Victory-card policy, independent of the build and opening blocks."""

    province_mode: Literal["always", "threshold"] = "always"
    province_threshold: int = 8
    duchy_mode: Literal["never", "threshold", "always"] = "threshold"
    duchy_threshold: int = 4
    estate_mode: Literal["never", "threshold", "pile_pressure"] = "never"
    estate_threshold: int = 2
    estate_empty_piles: int = 2


@dataclass
class EndgamePlan:
    """Policies whose purpose is ending or denying the game, not deck growth."""

    estate_pileout: bool = False
    pileout_max_remaining: int = 1
    pileout_min_score_diff: int = 0


@dataclass
class TrashPlan:
    trash_curse: bool = True
    estate_until_provinces: int | None = 4
    copper_after_treasures: int | None = 3


@dataclass
class StrategicGenome:
    """A complete high-level strategy that compiles to priority lists."""

    openings: list[OpeningTarget] = field(default_factory=list)
    build_targets: list[BuildTarget] = field(default_factory=list)
    economy: EconomyPlan = field(default_factory=EconomyPlan)
    greening: GreeningPlan = field(default_factory=GreeningPlan)
    endgame: EndgamePlan = field(default_factory=EndgamePlan)
    trash: TrashPlan = field(default_factory=TrashPlan)
    action_order: list[str] = field(default_factory=list)
    treasure_order: list[str] = field(default_factory=list)

    def compile_into(self, strategy: BaseStrategy, info) -> BaseStrategy:
        """Replace phenotype rule lists while preserving identity and Ways."""

        gain: list[PriorityRule] = []

        # A pile-out rule must precede normal green: its purpose is to take a
        # cheaper card even when Province is affordable.
        if self.endgame.estate_pileout:
            gain.append(
                PriorityRule(
                    "Estate",
                    PriorityRule.and_(
                        PriorityRule.empty_piles(">=", 2),
                        PriorityRule.pile_count(
                            "Estate", "<=", self.endgame.pileout_max_remaining
                        ),
                        PriorityRule.score_diff(">=", self.endgame.pileout_min_score_diff),
                    ),
                )
            )

        # Explicit opening rules sit above green/build rules.  The max-in-deck
        # condition makes "one Chapel on turns 1-2" a single reachable edit.
        for opening in self.openings:
            gain.append(
                PriorityRule(
                    opening.card,
                    PriorityRule.and_(
                        PriorityRule.max_in_deck(opening.card, opening.copies),
                        PriorityRule.turn_number("<=", opening.through_turn),
                    ),
                )
            )

        def compile_target(target: BuildTarget) -> PriorityRule:
            target.normalize_timing()
            conditions = [PriorityRule.max_in_deck(target.card, target.copies)]
            if target.from_turn is not None:
                conditions.append(PriorityRule.turn_number(">=", target.from_turn))
            if target.through_turn is not None:
                conditions.append(PriorityRule.turn_number("<=", target.through_turn))
            if target.while_provinces_above is not None:
                conditions.append(
                    PriorityRule.provinces_left(">", target.while_provinces_above)
                )
            if target.requires_card is not None:
                conditions.append(PriorityRule.has_cards([target.requires_card], 1))
            condition = (
                conditions[0]
                if len(conditions) == 1
                else PriorityRule.and_(*conditions)
            )
            return PriorityRule(target.card, condition)

        gain.extend(
            compile_target(target)
            for target in self.build_targets
            if target.priority_band == "before_province"
        )

        if info.has_colony:
            gain.append(PriorityRule("Colony"))

        if self.greening.province_mode == "always":
            gain.append(PriorityRule("Province"))
        else:
            gain.append(
                PriorityRule(
                    "Province",
                    PriorityRule.provinces_left("<=", self.greening.province_threshold),
                )
            )

        gain.extend(
            compile_target(target)
            for target in self.build_targets
            if target.priority_band == "before_duchy"
        )

        if self.greening.duchy_mode == "always":
            gain.append(PriorityRule("Duchy"))
        elif self.greening.duchy_mode == "threshold":
            gain.append(
                PriorityRule(
                    "Duchy",
                    PriorityRule.provinces_left("<=", self.greening.duchy_threshold),
                )
            )

        if self.greening.estate_mode == "threshold":
            gain.append(
                PriorityRule(
                    "Estate",
                    PriorityRule.provinces_left("<=", self.greening.estate_threshold),
                )
            )
        elif self.greening.estate_mode == "pile_pressure":
            gain.append(
                PriorityRule(
                    "Estate",
                    PriorityRule.empty_piles(
                        ">=", self.greening.estate_empty_piles
                    ),
                )
            )

        gain.extend(
            compile_target(target)
            for target in self.build_targets
            if target.priority_band == "build"
        )

        if info.has_platinum and self.economy.prefer_platinum:
            gain.append(PriorityRule("Platinum"))
        gold_condition = (
            PriorityRule.max_in_deck("Gold", self.economy.gold_cap)
            if self.economy.gold_cap is not None
            else None
        )
        if self.economy.buy_gold:
            gain.append(PriorityRule("Gold", gold_condition))

        gain.extend(
            compile_target(target)
            for target in self.build_targets
            if target.priority_band == "before_silver"
        )

        silver_conditions = []
        if self.economy.silver_cap is not None:
            silver_conditions.append(
                PriorityRule.max_in_deck("Silver", self.economy.silver_cap)
            )
        if self.economy.silver_through_turn is not None:
            silver_conditions.append(
                PriorityRule.turn_number("<=", self.economy.silver_through_turn)
            )
        if self.economy.buy_silver:
            silver_condition = None
            if len(silver_conditions) == 1:
                silver_condition = silver_conditions[0]
            elif silver_conditions:
                silver_condition = PriorityRule.and_(*silver_conditions)
            gain.append(
                PriorityRule(
                    "Silver",
                    silver_condition,
                )
            )
        gain.extend(
            compile_target(target)
            for target in self.build_targets
            if target.priority_band == "fallback"
        )
        strategy.gain_priority = gain
        strategy.action_priority = [PriorityRule(card) for card in self.action_order]
        strategy.treasure_priority = [PriorityRule(card) for card in self.treasure_order]

        trash: list[PriorityRule] = []
        if self.trash.trash_curse:
            trash.append(PriorityRule("Curse"))
        if self.trash.estate_until_provinces is not None:
            trash.append(
                PriorityRule(
                    "Estate",
                    PriorityRule.provinces_left(">", self.trash.estate_until_provinces),
                )
            )
        if self.trash.copper_after_treasures is not None:
            trash.append(
                PriorityRule(
                    "Copper",
                    PriorityRule.has_cards(
                        ["Silver", "Gold"], self.trash.copper_after_treasures
                    ),
                )
            )
        strategy.trash_priority = trash
        strategy._strategic_genome = deepcopy(self)
        return strategy


def _rule_signature(rule: PriorityRule) -> tuple[str, str | None]:
    condition = getattr(rule, "condition", None)
    return (
        rule.card_name,
        getattr(condition, "_source", None) if condition is not None else None,
    )


def _strategy_rule_signature(strategy: BaseStrategy) -> tuple[tuple, ...]:
    """Behavioral signature for the rule lists owned by a strategic genome."""

    return tuple(
        tuple(_rule_signature(rule) for rule in getattr(strategy, attr, []) or [])
        for attr in (
            "gain_priority",
            "action_priority",
            "treasure_priority",
            "trash_priority",
        )
    )


_SIMPLE_PROVINCE_GATE_RE = re.compile(
    r"^PriorityRule\.provinces_left\('<=', (\d+)\)$"
)
_ESTATE_PRESSURE_RE = re.compile(
    r"^PriorityRule\.empty_piles\('>=', (\d+)\)$"
)
_MAX_IN_DECK_RE = re.compile(
    r"PriorityRule\.max_in_deck\('([^']+)', (\d+)\)"
)
_TURN_GATE_RE = re.compile(
    r"PriorityRule\.turn_number\('(<=|>=)', (\d+)\)"
)
_PROVINCES_ABOVE_RE = re.compile(
    r"PriorityRule\.provinces_left\('>', (\d+)\)"
)
_REQUIRES_CARD_RE = re.compile(
    r"PriorityRule\.has_cards\(\['([^']+)'\], 1\)"
)
_PILEOUT_RE = re.compile(
    r"^PriorityRule\.and_\(PriorityRule\.empty_piles\('>=', 2\), "
    r"PriorityRule\.pile_count\('Estate', '<=', (\d+)\), "
    r"PriorityRule\.score_diff\('>=', (-?\d+)\)\)$"
)
_SILVER_CAP_RE = re.compile(
    r"PriorityRule\.max_in_deck\('Silver', (\d+)\)"
)
_SILVER_TURN_RE = re.compile(
    r"PriorityRule\.turn_number\('<=', (\d+)\)"
)
_GOLD_CAP_RE = re.compile(
    r"^PriorityRule\.max_in_deck\('Gold', (\d+)\)$"
)
_TRASH_ESTATE_RE = re.compile(
    r"^PriorityRule\.provinces_left\('>', (\d+)\)$"
)
_TRASH_COPPER_RE = re.compile(
    r"^PriorityRule\.has_cards\(\['Silver', 'Gold'\], (\d+)\)$"
)


def promote_legacy_strategy(strategy: BaseStrategy, info) -> bool:
    """Attach typed metadata when a legacy strategy round-trips exactly.

    Promotion is intentionally conservative.  We infer only shapes emitted by
    :meth:`StrategicGenome.compile_into`, compile the inferred genome into a
    probe, and attach it only if every owned rule list has the same ordered
    card/condition signature.  Unsupported custom hooks and conditional action
    rules therefore remain on the compatibility path without behavioral drift.
    """

    if getattr(strategy, "_strategic_genome", None) is not None:
        return True

    gain = list(getattr(strategy, "gain_priority", []) or [])
    action = list(getattr(strategy, "action_priority", []) or [])
    treasure = list(getattr(strategy, "treasure_priority", []) or [])
    trash = list(getattr(strategy, "trash_priority", []) or [])

    if any(rule.condition is not None for rule in action + treasure):
        return False

    province_rules = [rule for rule in gain if rule.card_name == "Province"]
    if len(province_rules) != 1:
        return False
    province_source = _rule_signature(province_rules[0])[1]
    if province_source is None:
        province_mode, province_threshold = "always", 8
    else:
        match = _SIMPLE_PROVINCE_GATE_RE.fullmatch(province_source)
        if match is None:
            return False
        province_mode, province_threshold = "threshold", int(match.group(1))

    duchy_rules = [rule for rule in gain if rule.card_name == "Duchy"]
    if len(duchy_rules) > 1:
        return False
    if not duchy_rules:
        duchy_mode, duchy_threshold = "never", 4
    else:
        duchy_source = _rule_signature(duchy_rules[0])[1]
        if duchy_source is None:
            duchy_mode, duchy_threshold = "always", 4
        else:
            match = _SIMPLE_PROVINCE_GATE_RE.fullmatch(duchy_source)
            if match is None:
                return False
            duchy_mode, duchy_threshold = "threshold", int(match.group(1))

    estate_mode: Literal["never", "threshold", "pile_pressure"] = "never"
    estate_threshold = 2
    estate_empty_piles = 2
    endgame = EndgamePlan()
    for rule in (rule for rule in gain if rule.card_name == "Estate"):
        source = _rule_signature(rule)[1]
        threshold_match = _SIMPLE_PROVINCE_GATE_RE.fullmatch(source or "")
        pressure_match = _ESTATE_PRESSURE_RE.fullmatch(source or "")
        pileout_match = _PILEOUT_RE.fullmatch(source or "")
        if threshold_match and estate_mode == "never":
            estate_mode = "threshold"
            estate_threshold = int(threshold_match.group(1))
        elif pressure_match and estate_mode == "never":
            estate_mode = "pile_pressure"
            estate_empty_piles = int(pressure_match.group(1))
        elif pileout_match and not endgame.estate_pileout:
            endgame = EndgamePlan(
                estate_pileout=True,
                pileout_max_remaining=int(pileout_match.group(1)),
                pileout_min_score_diff=int(pileout_match.group(2)),
            )
        else:
            return False

    gold_rules = [rule for rule in gain if rule.card_name == "Gold"]
    silver_rules = [rule for rule in gain if rule.card_name == "Silver"]
    platinum_rules = [rule for rule in gain if rule.card_name == "Platinum"]
    if any(len(rules) > 1 for rules in (gold_rules, silver_rules, platinum_rules)):
        return False

    gold_cap = None
    if gold_rules and gold_rules[0].condition is not None:
        match = _GOLD_CAP_RE.fullmatch(_rule_signature(gold_rules[0])[1] or "")
        if match is None:
            return False
        gold_cap = int(match.group(1))

    silver_cap = silver_through_turn = None
    if silver_rules and silver_rules[0].condition is not None:
        source = _rule_signature(silver_rules[0])[1] or ""
        cap_match = _SILVER_CAP_RE.search(source)
        turn_match = _SILVER_TURN_RE.search(source)
        silver_cap = int(cap_match.group(1)) if cap_match else None
        silver_through_turn = int(turn_match.group(1)) if turn_match else None
        if silver_cap is None and silver_through_turn is None:
            return False

    province_index = gain.index(province_rules[0])
    duchy_index = gain.index(duchy_rules[0]) if duchy_rules else len(gain)
    economy_indexes = [
        index for index, rule in enumerate(gain)
        if rule.card_name in {"Platinum", "Gold", "Silver"}
    ]
    first_economy_index = min(economy_indexes, default=len(gain))
    silver_index = gain.index(silver_rules[0]) if silver_rules else len(gain)
    basic = {"Colony", "Province", "Duchy", "Estate", "Platinum", "Gold", "Silver"}
    openings: list[OpeningTarget] = []
    targets: list[BuildTarget] = []
    for index, rule in enumerate(gain):
        if rule.card_name in basic:
            continue
        source = _rule_signature(rule)[1] or ""
        cap_match = _MAX_IN_DECK_RE.search(source)
        if cap_match is None or cap_match.group(1) != rule.card_name:
            return False
        copies = int(cap_match.group(2))
        turn_matches = _TURN_GATE_RE.findall(source)
        from_turn = next((int(n) for op, n in turn_matches if op == ">="), None)
        through_turn = next((int(n) for op, n in turn_matches if op == "<="), None)
        provinces_match = _PROVINCES_ABOVE_RE.search(source)
        requires_match = _REQUIRES_CARD_RE.search(source)

        # OpeningTarget is the exact early-window shape emitted before green.
        if (
            index < province_index
            and from_turn is None
            and through_turn is not None
            and provinces_match is None
            and requires_match is None
        ):
            openings.append(OpeningTarget(rule.card_name, copies, through_turn))
            continue

        band: Literal[
            "before_province", "before_duchy", "build", "before_silver", "fallback"
        ]
        if index < province_index:
            band = "before_province"
        elif duchy_rules and index < duchy_index:
            band = "before_duchy"
        elif index < first_economy_index:
            band = "build"
        elif index < silver_index:
            band = "before_silver"
        else:
            band = "fallback"
        targets.append(
            BuildTarget(
                rule.card_name,
                copies,
                from_turn=from_turn,
                through_turn=through_turn,
                while_provinces_above=(
                    int(provinces_match.group(1)) if provinces_match else None
                ),
                requires_card=(requires_match.group(1) if requires_match else None),
                priority_band=band,
            )
        )

    trash_plan = TrashPlan(
        trash_curse=False,
        estate_until_provinces=None,
        copper_after_treasures=None,
    )
    for rule in trash:
        source = _rule_signature(rule)[1]
        if rule.card_name == "Curse" and source is None and not trash_plan.trash_curse:
            trash_plan.trash_curse = True
        elif rule.card_name == "Estate":
            match = _TRASH_ESTATE_RE.fullmatch(source or "")
            if match is None or trash_plan.estate_until_provinces is not None:
                return False
            trash_plan.estate_until_provinces = int(match.group(1))
        elif rule.card_name == "Copper":
            match = _TRASH_COPPER_RE.fullmatch(source or "")
            if match is None or trash_plan.copper_after_treasures is not None:
                return False
            trash_plan.copper_after_treasures = int(match.group(1))
        else:
            return False

    genome = StrategicGenome(
        openings=openings,
        build_targets=targets,
        economy=EconomyPlan(
            buy_gold=bool(gold_rules),
            buy_silver=bool(silver_rules),
            silver_cap=silver_cap,
            silver_through_turn=silver_through_turn,
            gold_cap=gold_cap,
            prefer_platinum=bool(platinum_rules),
        ),
        greening=GreeningPlan(
            province_mode=province_mode,
            province_threshold=province_threshold,
            duchy_mode=duchy_mode,
            duchy_threshold=duchy_threshold,
            estate_mode=estate_mode,
            estate_threshold=estate_threshold,
            estate_empty_piles=estate_empty_piles,
        ),
        endgame=endgame,
        trash=trash_plan,
        action_order=[rule.card_name for rule in action],
        treasure_order=[rule.card_name for rule in treasure],
    )
    probe = genome.compile_into(BaseStrategy(), info)
    if _strategy_rule_signature(probe) != _strategy_rule_signature(strategy):
        return False
    strategy._strategic_genome = deepcopy(genome)
    return True


def synchronize_strategic_genome(strategy: BaseStrategy, info) -> bool:
    """Reconcile typed modules with a simplified or empirically pruned phenotype.

    Simplification and rule pruning operate on compiled priority lists. Without
    this reconciliation, semantic crossover would compile the pre-pruning
    modules and resurrect removed rules. The phenotype remains authoritative:
    modules whose compiled rules disappeared are removed or disabled, while
    surviving action and Treasure order is copied back verbatim.

    Returns ``False`` for legacy strategies without typed metadata.
    """

    original = getattr(strategy, "_strategic_genome", None)
    if original is None:
        return False
    genome = deepcopy(original)
    gain_signatures = {_rule_signature(rule) for rule in strategy.gain_priority}
    action_names = [rule.card_name for rule in strategy.action_priority]
    treasure_names = [rule.card_name for rule in strategy.treasure_priority]
    trash_signatures = {_rule_signature(rule) for rule in strategy.trash_priority}

    # Match typed entries by compiling each one in isolation. This avoids
    # relying on positions that differ across opening/green priority bands.
    kept_openings = []
    for opening in genome.openings:
        probe = StrategicGenome(
            openings=[deepcopy(opening)],
            greening=GreeningPlan(duchy_mode="never"),
            economy=EconomyPlan(buy_gold=False, buy_silver=False),
        ).compile_into(BaseStrategy(), info)
        signature = next(
            (_rule_signature(rule) for rule in probe.gain_priority if rule.card_name == opening.card),
            None,
        )
        if signature in gain_signatures:
            kept_openings.append(opening)
    genome.openings = kept_openings

    kept_targets = []
    for target in genome.build_targets:
        probe = StrategicGenome(
            build_targets=[deepcopy(target)],
            greening=GreeningPlan(duchy_mode="never"),
            economy=EconomyPlan(buy_gold=False, buy_silver=False),
        ).compile_into(BaseStrategy(), info)
        signature = next(
            (_rule_signature(rule) for rule in probe.gain_priority if rule.card_name == target.card),
            None,
        )
        if signature in gain_signatures:
            kept_targets.append(target)
    genome.build_targets = kept_targets

    def compiled_rule_survives(probe_genome: StrategicGenome, card: str) -> bool:
        """Whether this isolated module's exact compiled rule survived."""
        probe = probe_genome.compile_into(BaseStrategy(), info)
        return any(
            _rule_signature(rule) in gain_signatures
            for rule in probe.gain_priority
            if rule.card_name == card
        )

    duchy_probe = StrategicGenome(
        greening=GreeningPlan(
            duchy_mode=genome.greening.duchy_mode,
            duchy_threshold=genome.greening.duchy_threshold,
            estate_mode="never",
        ),
        economy=EconomyPlan(buy_gold=False, buy_silver=False),
    )
    if not compiled_rule_survives(duchy_probe, "Duchy"):
        genome.greening.duchy_mode = "never"

    estate_probe = StrategicGenome(
        greening=GreeningPlan(
            duchy_mode="never",
            estate_mode=genome.greening.estate_mode,
            estate_threshold=genome.greening.estate_threshold,
            estate_empty_piles=genome.greening.estate_empty_piles,
        ),
        economy=EconomyPlan(buy_gold=False, buy_silver=False),
    )
    if not compiled_rule_survives(estate_probe, "Estate"):
        genome.greening.estate_mode = "never"

    endgame_probe = StrategicGenome(
        greening=GreeningPlan(duchy_mode="never", estate_mode="never"),
        endgame=deepcopy(genome.endgame),
        economy=EconomyPlan(buy_gold=False, buy_silver=False),
    )
    if not compiled_rule_survives(endgame_probe, "Estate"):
        genome.endgame.estate_pileout = False

    gold_probe = StrategicGenome(
        greening=GreeningPlan(duchy_mode="never"),
        economy=EconomyPlan(
            buy_gold=genome.economy.buy_gold,
            buy_silver=False,
            gold_cap=genome.economy.gold_cap,
            prefer_platinum=False,
        ),
    )
    genome.economy.buy_gold = compiled_rule_survives(gold_probe, "Gold")
    silver_probe = StrategicGenome(
        greening=GreeningPlan(duchy_mode="never"),
        economy=EconomyPlan(
            buy_gold=False,
            buy_silver=genome.economy.buy_silver,
            silver_cap=genome.economy.silver_cap,
            silver_through_turn=genome.economy.silver_through_turn,
            prefer_platinum=False,
        ),
    )
    genome.economy.buy_silver = compiled_rule_survives(silver_probe, "Silver")
    platinum_probe = StrategicGenome(
        greening=GreeningPlan(duchy_mode="never"),
        economy=EconomyPlan(
            buy_gold=False,
            buy_silver=False,
            prefer_platinum=genome.economy.prefer_platinum,
        ),
    )
    genome.economy.prefer_platinum = compiled_rule_survives(
        platinum_probe, "Platinum"
    )

    genome.action_order = [card for card in action_names if card in genome.action_order]
    genome.treasure_order = [card for card in treasure_names if card in genome.treasure_order]
    genome.trash.trash_curse = any(card == "Curse" for card, _ in trash_signatures)
    if not any(card == "Estate" for card, _ in trash_signatures):
        genome.trash.estate_until_provinces = None
    if not any(card == "Copper" for card, _ in trash_signatures):
        genome.trash.copper_after_treasures = None

    strategy._strategic_genome = genome
    return True


def _default_action_order(info, rng) -> list[str]:
    ordered: list[str] = []
    for source in (info.villages, info.cantrips, info.terminal_draw, info.other_terminals):
        group = list(source)
        rng.shuffle(group)
        ordered.extend(group)
    return ordered


def _reachable_dependency_cards(
    genome: StrategicGenome,
    info,
    *,
    without_target: BuildTarget | None = None,
) -> set[str]:
    """Return cards obtainable without relying on ``without_target``.

    Openings and enabled economy cards are roots. Unconditional build targets
    add more roots, and conditional targets become reachable once their anchor
    is reachable. Excluding the target being re-gated prevents selecting a
    prerequisite whose own acquisition transitively depends on that target.
    """

    reachable = {opening.card for opening in genome.openings}
    if genome.economy.buy_gold:
        reachable.add("Gold")
    if genome.economy.buy_silver:
        reachable.add("Silver")
    if info.has_platinum and genome.economy.prefer_platinum:
        reachable.add("Platinum")

    pending = [
        target
        for target in genome.build_targets
        if target is not without_target
    ]
    while pending:
        newly_reachable = [
            target
            for target in pending
            if target.requires_card is None or target.requires_card in reachable
        ]
        if not newly_reachable:
            break
        reachable.update(target.card for target in newly_reachable)
        reached_ids = {id(target) for target in newly_reachable}
        pending = [target for target in pending if id(target) not in reached_ids]
    return reachable


def _normalize_build_dependencies(genome: StrategicGenome, info) -> None:
    """Remove dependencies that became unreachable or cyclic after edits."""

    for target in genome.build_targets:
        if (
            target.requires_card is not None
            and target.requires_card
            not in _reachable_dependency_cards(
                genome, info, without_target=target
            )
        ):
            target.requires_card = None


def random_strategic_genome(info, rng=_random_module) -> StrategicGenome:
    """Create a coherent but diverse phase-aware strategic hypothesis."""

    openings: list[OpeningTarget] = []
    opening_candidates = [
        card for card in info.gainable if infer_card_roles(card).has("trasher")
    ]
    if opening_candidates and rng.random() < 0.45:
        openings.append(OpeningTarget(rng.choice(opening_candidates), 1, rng.randint(2, 4)))

    picks = list(info.gainable)
    rng.shuffle(picks)
    picks = picks[: rng.randint(min(2, len(picks)), min(6, len(picks)))] if picks else []
    targets = [
        BuildTarget(
            card=card,
            copies=info.default_cap(card, rng),
            from_turn=rng.randint(3, 10) if rng.random() < 0.1 else None,
            through_turn=rng.randint(8, 16) if rng.random() < 0.2 else None,
            while_provinces_above=rng.randint(2, 4) if rng.random() < 0.2 else None,
            priority_band=rng.choices(
                ["build", "before_silver", "fallback", "before_duchy", "before_province"],
                weights=[0.55, 0.2, 0.05, 0.15, 0.05],
                k=1,
            )[0],
        )
        for card in picks
    ]
    targets.sort(key=lambda target: info.costs.get(target.card, 0), reverse=True)
    for index, target in enumerate(targets):
        # Earlier targets are reachable by construction, so dependencies form
        # a directed acyclic graph. Openings are independent roots.
        anchors = list(
            dict.fromkeys(
                [opening.card for opening in openings]
                + [other.card for other in targets[:index]]
            )
        )
        if anchors and rng.random() < 0.15:
            target.requires_card = rng.choice(anchors)

    province_mode = "always" if rng.random() < 0.8 else "threshold"
    duchy_roll = rng.random()
    duchy_mode: Literal["never", "threshold", "always"]
    if duchy_roll < 0.1:
        duchy_mode = "never"
    elif duchy_roll < 0.22:
        duchy_mode = "always"
    else:
        duchy_mode = "threshold"

    treasures = (
        (["Platinum"] if info.has_platinum else [])
        + ["Gold"]
        + sorted(info.treasure_cards, key=lambda c: -info.costs.get(c, 0))
        + ["Silver", "Copper"]
    )
    return StrategicGenome(
        openings=openings,
        build_targets=targets,
        economy=EconomyPlan(
            buy_gold=rng.random() >= 0.1,
            silver_cap=rng.randint(3, 6) if rng.random() < 0.35 else None,
            silver_through_turn=rng.randint(7, 13) if rng.random() < 0.25 else None,
            gold_cap=rng.randint(2, 6) if rng.random() < 0.15 else None,
        ),
        greening=GreeningPlan(
            province_mode=province_mode,
            province_threshold=rng.randint(4, 8),
            duchy_mode=duchy_mode,
            duchy_threshold=rng.randint(3, 6),
            estate_mode=rng.choices(
                ["never", "threshold", "pile_pressure"],
                weights=[0.55, 0.35, 0.1],
                k=1,
            )[0],
            estate_threshold=rng.randint(1, 3),
            estate_empty_piles=rng.randint(1, 2),
        ),
        endgame=EndgamePlan(
            estate_pileout=rng.random() < 0.12,
            pileout_max_remaining=1,
            pileout_min_score_diff=rng.choice([-3, 0, 3]),
        ),
        action_order=_default_action_order(info, rng),
        treasure_order=treasures,
    )


def random_strategic_strategy(info, rng=_random_module) -> BaseStrategy:
    strategy = BaseStrategy()
    return random_strategic_genome(info, rng).compile_into(strategy, info)


def mutate_strategic_strategy(strategy: BaseStrategy, info, rate: float, rng=_random_module) -> bool:
    """Apply semantic edits and recompile. Return False for legacy phenotypes."""

    genome = getattr(strategy, "_strategic_genome", None)
    if genome is None:
        return False
    genome = deepcopy(genome)

    if rng.random() < rate:
        modes = ["never", "threshold", "always"]
        genome.greening.duchy_mode = rng.choice(modes)
    if rng.random() < rate:
        genome.greening.duchy_threshold = rng.randint(2, 8)
    if rng.random() < rate * 0.5:
        genome.greening.province_mode = rng.choice(["always", "threshold"])
        genome.greening.province_threshold = rng.randint(3, 8)
    if rng.random() < rate * 0.5:
        genome.greening.estate_mode = rng.choice(
            ["never", "threshold", "pile_pressure"]
        )
        genome.greening.estate_threshold = rng.randint(1, 5)
        genome.greening.estate_empty_piles = rng.randint(1, 2)
    if rng.random() < rate * 0.5:
        genome.endgame.estate_pileout = not genome.endgame.estate_pileout
        genome.endgame.pileout_min_score_diff = rng.choice([-6, -3, 0, 3, 6])

    if rng.random() < rate and genome.build_targets:
        target = rng.choice(genome.build_targets)
        target.copies = max(1, min(10, target.copies + rng.choice([-1, 1])))
    if rng.random() < rate * 0.5 and genome.build_targets:
        target = rng.choice(genome.build_targets)
        target.priority_band = rng.choice(
            ["before_province", "before_duchy", "build", "before_silver", "fallback"]
        )
    if rng.random() < rate * 0.4 and genome.build_targets:
        target = rng.choice(genome.build_targets)
        target.from_turn = rng.choice([None, 3, 5, 7, 9, 11])
    if rng.random() < rate * 0.4 and genome.build_targets:
        target = rng.choice(genome.build_targets)
        target.through_turn = rng.choice([None, 6, 8, 10, 12, 16])
    if rng.random() < rate * 0.4 and genome.build_targets:
        target = rng.choice(genome.build_targets)
        target.while_provinces_above = rng.choice([None, 2, 3, 4, 5, 6])
    if rng.random() < rate * 0.3 and genome.build_targets:
        target = rng.choice(genome.build_targets)
        anchors = sorted(
            _reachable_dependency_cards(
                genome, info, without_target=target
            )
        )
        target.requires_card = rng.choice([None, *anchors]) if anchors else None
    if rng.random() < rate and len(genome.build_targets) >= 2:
        i = rng.randint(0, len(genome.build_targets) - 2)
        genome.build_targets[i], genome.build_targets[i + 1] = (
            genome.build_targets[i + 1], genome.build_targets[i]
        )
    if rng.random() < rate * 0.4:
        existing = {target.card for target in genome.build_targets}
        missing = [card for card in info.gainable if card not in existing]
        if missing:
            card = rng.choice(missing)
            genome.build_targets.append(BuildTarget(card, info.default_cap(card, rng)))
    if rng.random() < rate * 0.25 and len(genome.build_targets) > 2:
        genome.build_targets.pop(rng.randrange(len(genome.build_targets)))

    if rng.random() < rate * 0.35:
        if genome.openings and rng.random() < 0.5:
            opening = rng.choice(genome.openings)
            opening.through_turn = rng.randint(2, 5)
            opening.copies = rng.randint(1, 2)
        else:
            candidates = [
                card for card in info.gainable
                if all(opening.card != card for opening in genome.openings)
            ]
            if candidates:
                genome.openings.append(OpeningTarget(rng.choice(candidates), 1, rng.randint(2, 4)))
    if rng.random() < rate * 0.15 and genome.openings:
        genome.openings.pop(rng.randrange(len(genome.openings)))

    if rng.random() < rate and len(genome.action_order) >= 2:
        i = rng.randint(0, len(genome.action_order) - 2)
        genome.action_order[i], genome.action_order[i + 1] = (
            genome.action_order[i + 1], genome.action_order[i]
        )
    if rng.random() < rate * 0.5:
        genome.economy.silver_cap = rng.choice([None, 2, 3, 4, 5, 6])
    if rng.random() < rate * 0.4:
        genome.economy.silver_through_turn = rng.choice(
            [None, 5, 7, 9, 11, 13, 16]
        )
    if rng.random() < rate * 0.25:
        genome.economy.buy_gold = not genome.economy.buy_gold
    if rng.random() < rate * 0.2:
        genome.economy.buy_silver = not genome.economy.buy_silver
    if rng.random() < rate * 0.35:
        genome.economy.gold_cap = rng.choice([None, 1, 2, 3, 4, 5, 6])
    if info.has_platinum and rng.random() < rate * 0.2:
        genome.economy.prefer_platinum = not genome.economy.prefer_platinum
    if rng.random() < rate * 0.5:
        genome.trash.estate_until_provinces = rng.choice([None, 3, 4, 5, 6])
    if rng.random() < rate * 0.3:
        genome.trash.trash_curse = not genome.trash.trash_curse
    if rng.random() < rate * 0.4:
        genome.trash.copper_after_treasures = rng.choice([None, 2, 3, 4, 5])
    if rng.random() < rate and len(genome.treasure_order) >= 2:
        i = rng.randint(0, len(genome.treasure_order) - 2)
        genome.treasure_order[i], genome.treasure_order[i + 1] = (
            genome.treasure_order[i + 1], genome.treasure_order[i]
        )

    # Later mutations can remove a target/opening or disable an economy card
    # selected as an anchor. Revalidate after the complete semantic edit.
    _normalize_build_dependencies(genome, info)

    way_policy = deepcopy(getattr(strategy, "way_policy", []))
    name = strategy.name
    genome.compile_into(strategy, info)
    strategy.name = name
    strategy.way_policy = way_policy
    return True


def crossover_strategic_strategies(parent1: BaseStrategy, parent2: BaseStrategy, info, rng=_random_module) -> BaseStrategy | None:
    """Combine whole strategic modules, avoiding positional rule crossover."""

    first = getattr(parent1, "_strategic_genome", None)
    second = getattr(parent2, "_strategic_genome", None)
    if first is None or second is None:
        return None

    child_genome = deepcopy(first)
    for field_name in (
        "openings", "build_targets", "economy", "greening", "endgame",
        "trash", "action_order", "treasure_order",
    ):
        if rng.random() < 0.5:
            setattr(child_genome, field_name, deepcopy(getattr(second, field_name)))

    # Build targets can arrive from one parent while their opening or economy
    # roots arrive from the other. Do not compile stranded dependencies.
    _normalize_build_dependencies(child_genome, info)

    child = deepcopy(parent1)
    child_genome.compile_into(child, info)
    if rng.random() < 0.5:
        child.way_policy = deepcopy(getattr(parent2, "way_policy", []))
    return child
