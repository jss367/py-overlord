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
    through_turn: int | None = None
    while_provinces_above: int | None = None
    requires_card: str | None = None
    priority_band: Literal["before_province", "before_duchy", "build"] = "build"


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
    estate_mode: Literal["never", "threshold"] = "never"
    estate_threshold: int = 2


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
            conditions = [PriorityRule.max_in_deck(target.card, target.copies)]
            if target.through_turn is not None:
                conditions.append(PriorityRule.turn_number("<=", target.through_turn))
            if target.while_provinces_above is not None:
                conditions.append(
                    PriorityRule.provinces_left(">", target.while_provinces_above)
                )
            if target.requires_card is not None:
                conditions.append(PriorityRule.has_cards([target.requires_card], 1))
            return PriorityRule(target.card, PriorityRule.and_(*conditions))

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
            gain.append(
                PriorityRule(
                    "Silver",
                    PriorityRule.and_(*silver_conditions) if silver_conditions else None,
                )
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
            through_turn=rng.randint(8, 16) if rng.random() < 0.2 else None,
            while_provinces_above=rng.randint(2, 4) if rng.random() < 0.2 else None,
            priority_band=rng.choices(
                ["build", "before_duchy", "before_province"],
                weights=[0.75, 0.2, 0.05],
                k=1,
            )[0],
        )
        for card in picks
    ]
    targets.sort(key=lambda target: info.costs.get(target.card, 0), reverse=True)

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
            estate_mode="threshold" if rng.random() < 0.4 else "never",
            estate_threshold=rng.randint(1, 3),
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
        genome.greening.estate_mode = rng.choice(["never", "threshold"])
        genome.greening.estate_threshold = rng.randint(1, 5)
    if rng.random() < rate * 0.5:
        genome.endgame.estate_pileout = not genome.endgame.estate_pileout
        genome.endgame.pileout_min_score_diff = rng.choice([-6, -3, 0, 3, 6])

    if rng.random() < rate and genome.build_targets:
        target = rng.choice(genome.build_targets)
        target.copies = max(1, min(10, target.copies + rng.choice([-1, 1])))
    if rng.random() < rate * 0.5 and genome.build_targets:
        target = rng.choice(genome.build_targets)
        target.priority_band = rng.choice(
            ["before_province", "before_duchy", "build"]
        )
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
    if rng.random() < rate * 0.25:
        genome.economy.buy_gold = not genome.economy.buy_gold
    if rng.random() < rate * 0.5:
        genome.trash.estate_until_provinces = rng.choice([None, 3, 4, 5, 6])

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

    child = deepcopy(parent1)
    child_genome.compile_into(child, info)
    if rng.random() < 0.5:
        child.way_policy = deepcopy(getattr(parent2, "way_policy", []))
    return child
