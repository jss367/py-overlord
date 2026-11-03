"""Optional GEPA search over validated JSON strategic plans, never Python code.

The adapter keeps opponent matchups separate for Pareto selection. Final seed
selection uses the league's worst-tail aggregation on the *validation* cases;
held-out games are the caller's responsibility. Importing this module does not
require GEPA or an LLM provider.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass, fields
import hashlib
import json
from pathlib import Path
import random
import cloudpickle
from types import UnionType
from typing import Literal, get_args, get_origin, get_type_hints

from dominion.ai.genetic_ai import GeneticAI
from dominion.analysis.card_capabilities import kingdom_capabilities
from dominion.analysis.engine_archetypes import enumerate_engine_parts
from dominion.boards.loader import BoardConfig
from dominion.simulation.adversarial_league import aggregate_fitness
from dominion.simulation.strategic_genome import (
    BuildTarget,
    OpeningTarget,
    StrategicGenome,
)
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.simulation.parallel_games import GamePool, GameTask, chunk_games, resolve_workers
from dominion.simulation.simulation_budget import SimulationBudget
from dominion.simulation.structured_genome import BASIC_CARDS, KingdomInfo
from dominion.strategy.strategies.base_strategy import BaseStrategy


SCHEMA_VERSION = 2
_V2_FIELDS = {
    "StrategicGenome": {"treasure_reserve", "tactics"},
    "OpeningTarget": {"only_first_gain"},
    "BuildTarget": {"requires_copies", "balance_card", "balance_max_lead"},
    "GreeningPlan": {"province_colony_threshold", "province_from_turn", "colony_mode",
                     "colony_min_copies", "colony_fallback_turn"},
}

STRATEGY_REFLECTION_PROMPT = """Optimize a Dominion strategy configuration using actual simulator feedback.

Current complete strategy JSON:
<curr_param>

Board setup, supported schema, and evaluation feedback:
<side_info>

Propose a coordinated revision to the strategy configuration that can win
against these opponents. This is configuration/code optimization: the candidate
is a JSON strategic plan, not instructions or a prompt for another assistant.
Use only the decisions supported by the supplied schema and compiler. Retain
every required field and schema_version. Do not invent cards, fields, or code.
The representative loss is behavioral evidence, not proof of a unique cause.
Return ONLY the complete revised JSON object, without prose or Markdown fences.
"""


def genome_text(genome: StrategicGenome, schema_version: int = SCHEMA_VERSION) -> str:
    if schema_version not in (1, 2):
        raise ValueError("Unsupported schema version")
    def encode(value):
        if hasattr(value, "__dataclass_fields__"):
            omitted = _V2_FIELDS.get(type(value).__name__, set()) if schema_version == 1 else set()
            if any(getattr(value, key) != getattr(type(value)(), key) for key in omitted
                   if type(value).__name__ not in {"OpeningTarget", "BuildTarget"}):
                raise ValueError("Schema 1 cannot serialize schema 2 decisions")
            if schema_version == 1 and isinstance(value, OpeningTarget) and value.only_first_gain:
                raise ValueError("Schema 1 cannot serialize a first-gain opening")
            if isinstance(value, BuildTarget) and schema_version == 1 and (
                value.requires_copies != 1 or value.balance_card is not None or value.balance_max_lead != 0
            ):
                raise ValueError("Schema 1 cannot serialize counted or balanced targets")
            return {f.name: encode(getattr(value, f.name)) for f in fields(value) if f.name not in omitted}
        if isinstance(value, list):
            return [encode(item) for item in value]
        return value
    if schema_version == 1 and genome.greening.province_mode == "colony_or_turn":
        raise ValueError("Schema 1 cannot serialize Colony-or-turn greening")
    return json.dumps(
        {"schema_version": schema_version, "genome": encode(genome)},
        indent=2, sort_keys=True,
    )


def _decode(value, annotation, path, schema_version=SCHEMA_VERSION):
    """Strictly decode only the known dataclass schema, including nested types."""
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is UnionType:
        for option in args:
            try:
                return _decode(value, option, path, schema_version)
            except ValueError:
                pass
        raise ValueError(f"{path}: unexpected value {value!r}")
    if origin is Literal:
        if schema_version == 1 and path.endswith(".province_mode"):
            args = ("always", "threshold")
        if value not in args or type(value) is not type(args[0]):
            raise ValueError(f"{path}: expected one of {args}")
        return value
    if origin is list:
        if not isinstance(value, list) or len(value) > 40:
            raise ValueError(f"{path}: expected a list with at most 40 entries")
        return [_decode(item, args[0], f"{path}[{i}]", schema_version) for i, item in enumerate(value)]
    if hasattr(annotation, "__dataclass_fields__"):
        expected = {f.name for f in fields(annotation)}
        if schema_version == 1:
            expected -= _V2_FIELDS.get(annotation.__name__, set())
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError(f"{path}: expected exactly these fields: {sorted(expected)}")
        hints = get_type_hints(annotation)
        return annotation(**{
            key: _decode(item, hints[key], f"{path}.{key}", schema_version)
            for key, item in value.items()
        })
    if type(value) is not annotation:
        raise ValueError(f"{path}: expected {annotation.__name__}")
    if annotation is int:
        field = path.rsplit(".", 1)[-1]
        low, high = 0, 100
        if field in {"copies", "requires_copies", "colony_min_copies"}:
            low, high = 1, 10
        elif "turn" in field:
            low = 1
        elif "threshold" in field or "provinces" in field:
            high = 12
        elif "empty_piles" in field:
            high = 3
        elif field == "pileout_min_score_diff":
            low = -100
        elif field == "balance_max_lead":
            low, high = -10, 10
        if not low <= value <= high:
            raise ValueError(f"{path}: must be between {low} and {high}")
    return value


def parse_genome(text: str, info: KingdomInfo) -> StrategicGenome:
    if not isinstance(text, str) or len(text) > 40_000:
        raise ValueError("Candidate must be JSON text of at most 40,000 characters")
    try:
        payload = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise ValueError("Candidate must contain only a JSON object, without fences") from exc
    if (not isinstance(payload, dict) or set(payload) != {"schema_version", "genome"}
            or type(payload["schema_version"]) is not int
            or payload["schema_version"] not in (1, 2)):
        raise ValueError("Expected schema_version 1 or 2 and a genome object")
    genome = _decode(payload["genome"], StrategicGenome, "genome", payload["schema_version"])
    available = set(info.kingdom_cards) | (BASIC_CARDS - {"Colony", "Platinum"})
    for target in [*genome.openings, *genome.build_targets]:
        if target.card not in available:
            raise ValueError(f"Unavailable target card: {target.card}")
        if isinstance(target, BuildTarget):
            if target.requires_card is not None and target.requires_card not in available:
                raise ValueError(f"Unavailable dependency: {target.requires_card}")
            if target.balance_card is not None and target.balance_card not in available:
                raise ValueError(f"Unavailable balance card: {target.balance_card}")
            if (target.from_turn is not None and target.through_turn is not None
                    and target.from_turn > target.through_turn):
                raise ValueError("Build target from_turn must not exceed through_turn")
    orders = (
        (genome.action_order, set(info.action_cards), "action_order"),
        (genome.treasure_order, set(info.treasure_cards) | {"Copper", "Silver", "Gold"}
         | ({"Platinum"} if info.has_platinum else set()), "treasure_order"),
        (genome.bounty_exile_order, available, "bounty_exile_order"),
    )
    for order, allowed, label in orders:
        if len(order) != len(set(order)) or not set(order) <= allowed:
            raise ValueError(f"{label}: duplicate, unavailable, or wrong-role cards")
    if (genome.greening.colony_mode != "always" or genome.greening.province_mode == "colony_or_turn") and not info.has_colony:
        raise ValueError("Colony greening requires a Colony board")
    def validate_targets(targets):
        if not targets or len({t.card for t in targets}) != len(targets):
            raise ValueError("Gain targets must be nonempty and distinct")
        if any(t.card not in available for t in targets):
            raise ValueError("Unavailable gain target")
    if genome.treasure_reserve is not None:
        reserve = genome.treasure_reserve
        caps = kingdom_capabilities(info.kingdom_cards)
        if (reserve.treasure not in genome.treasure_order or reserve.gainer not in caps
                or not caps[reserve.gainer].is_gainer):
            raise ValueError("Treasure reserve requires an ordered Treasure and available gainer")
        validate_targets(reserve.targets)
    source = genome.tactics.balanced_gain_source
    if source is None and genome.tactics.balanced_gain_targets:
        raise ValueError("Balanced gain targets require a source")
    if source is not None:
        # Anvil is the audited source using the unified free-gain interface.
        if source != "Anvil" or source not in available:
            raise ValueError("Balanced gain source must be an available Anvil")
        validate_targets(genome.tactics.balanced_gain_targets)
    caps = kingdom_capabilities(info.kingdom_cards)
    multipliers = genome.tactics.protected_multipliers
    if len(multipliers) != len(set(multipliers)) or any(
        name not in info.action_cards or not caps[name].is_multiplier for name in multipliers
    ):
        raise ValueError("Protected multipliers must be distinct available Action multipliers")
    return genome


def compile_genome(text: str, info: KingdomInfo, name="Reflective search candidate") -> BaseStrategy:
    strategy = BaseStrategy()
    strategy.name = name
    strategy.description = "Experimental strategy compiled from a validated JSON strategic plan"
    return parse_genome(text, info).compile_into(strategy, info)


def board_seed(board: BoardConfig) -> StrategicGenome:
    """A board-derived typed seed; no hand-written strategy library is copied."""
    info = KingdomInfo.from_kingdom(board.kingdom_cards)
    genome = StrategicGenome()
    parts = enumerate_engine_parts(board, max_engines=1)
    if parts:
        engine = parts[0]
        if engine.gainer is not None:
            genome.openings = [OpeningTarget(engine.gainer.name, 1, 4)]
        for card in engine.chosen():
            count = 6 if card in (engine.village, engine.draw) else 2
            genome.build_targets.append(BuildTarget(
                card.name, count, priority_band="before_province",
            ))
    genome.action_order = list(info.villages) + [
        card for card in info.action_cards if card not in info.villages
    ]
    genome.treasure_order = (["Platinum"] if info.has_platinum else []) + [
        "Gold", "Silver", "Copper",
        *[card for card in info.treasure_cards if card != "Bank"],
        *(["Bank"] if "Bank" in info.treasure_cards else []),
    ]
    return genome


@dataclass(frozen=True)
class MatchupCase:
    opponent: str
    seed: int
    games: int
    split: str


def matchup_cases(opponents: dict, seed: int, games: int, split: str) -> list[MatchupCase]:
    if games < 2 or games % 2:
        raise ValueError("Games per opponent must be positive, complete seat pairs")
    offsets = {"train": 0, "validation": 1, "test": 2}
    if split not in offsets:
        raise ValueError(f"Unknown evaluation split: {split}")
    return [
        MatchupCase(name, game_seed(seed, offsets[split], i, 0), games, split)
        for i, name in enumerate(opponents)
    ]


def game_seed(*parts: int) -> int:
    """Stable seed blocks independent of candidate, seat, process, and Python hash."""
    return int.from_bytes(hashlib.sha256(repr(parts).encode()).digest()[:8], "big")


class MatchupEvaluator:
    """Seed-balanced games with real traces and explicit simulation accounting."""

    def __init__(self, board: BoardConfig, opponents: dict, log_dir: Path, *,
                 simulation_budget: SimulationBudget | None = None, budget_phase="reflection", workers=1):
        if not opponents:
            raise ValueError("At least one opponent is required")
        self.board = board
        self.info = KingdomInfo.from_kingdom(board.kingdom_cards)
        self.opponents = deepcopy(opponents)
        self.log_dir = Path(log_dir)
        self.simulated_games = 0
        self.records = []
        self.simulation_budget = simulation_budget
        self.budget_phase = budget_phase
        self.workers = resolve_workers(workers)
        self._pool = None

    def close(self):
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def _parallel_rows(self, strategy, opponent, case):
        if self._pool is None:
            with StrategyBattle(board_config=self.board, log_folder=str(self.log_dir / "workers"),
                                log_frequency=0) as battle:
                self._pool = GamePool(self.workers, battle.spec())
        games = [(index, game_seed(case.seed, index // 2)) for index in range(case.games)]
        tasks = [GameTask(i, cloudpickle.dumps(strategy), cloudpickle.dumps(opponent),
                          self.board.kingdom_cards, {}, chunk, fresh_strategy_per_game=True)
                 for i, chunk in enumerate(chunk_games(games, 4))]
        rows = []
        for result in self._pool.run(tasks).values():
            if isinstance(result, BaseException):
                raise RuntimeError("Reflective evaluation worker failed") from result
            if len(result.games) != len(tasks[result.task_id].games):
                raise RuntimeError("Reflective evaluation worker returned an incomplete task")
            for game in result.games:
                self.simulated_games += 1
                if self.simulation_budget is not None:
                    self.simulation_budget.consume(1, self.budget_phase)
                rows.append({"seed": game_seed(case.seed, game.game_num // 2), "seat": game.game_num % 2,
                             "won": game.won, "score": game.my_score, "opponent_score": game.opp_score,
                             "turns": game.turns, "log_path": None, "decision_firings": None})
        return rows

    def evaluate(self, strategy: BaseStrategy, case: MatchupCase, *, trace=False) -> dict:
        if case.opponent not in self.opponents:
            raise ValueError(f"Unknown opponent: {case.opponent}")
        if case.games < 2 or case.games % 2:
            raise ValueError("Matchups require complete seat pairs")
        if self.simulation_budget is not None:
            self.simulation_budget.require(case.games)
        strategy, opponent = deepcopy(strategy), deepcopy(self.opponents[case.opponent])
        strategy.name, opponent.name = "Candidate", "Opponent"
        rows = []
        saved_rng = random.getstate()
        folder = self.log_dir / f"evaluation-{len(self.records):05d}"
        try:
            if not trace and self.workers > 1:
                rows = self._parallel_rows(strategy, opponent, case)
            else:
                rows = self._serial_rows(strategy, opponent, case, folder, trace)
        finally:
            random.setstate(saved_rng)
        result = {
            "case": asdict(case), "games": rows,
            "win_rate": sum(row["won"] for row in rows) / case.games,
            "mean_score_margin": sum(row["score"] - row["opponent_score"] for row in rows) / case.games,
        }
        if trace:
            representative = next((row for row in rows if not row["won"]), rows[0])
            log = Path(representative["log_path"]).read_text() if representative["log_path"] else ""
            summaries = [line for line in log.splitlines() if "Summary:" in line]
            result["representative_game"] = {
                **representative,
                "log_excerpt": log[:1600] + "\n[excerpt]\n" + "\n".join(summaries[-16:]) + "\n" + log[-4400:],
            }
        self.records.append(result)
        return result

    def _serial_rows(self, strategy, opponent, case, folder, trace):
        rows = []
        with StrategyBattle(board_config=self.board, log_folder=str(folder),
                            log_frequency=1 if trace else 0) as battle:
            for index in range(case.games):
                random.seed(game_seed(case.seed, index // 2))
                me, other = GeneticAI(deepcopy(strategy)), GeneticAI(deepcopy(opponent))
                stats = battle._empty_decision_firings("Candidate")
                first, second = (me, other) if index % 2 == 0 else (other, me)
                winner, scores, log_path, turns = battle.run_game(
                    first, second, self.board.kingdom_cards,
                    decision_stats_by_ai={me: stats} if trace else None,
                )
                self.simulated_games += 1
                if self.simulation_budget is not None:
                    self.simulation_budget.consume(1, self.budget_phase)
                rows.append({
                    "seed": game_seed(case.seed, index // 2), "seat": index % 2,
                    "won": winner is me, "score": scores[me.name],
                    "opponent_score": scores[other.name], "turns": turns,
                    "log_path": log_path, "decision_firings": stats if trace else None,
                })
        return rows

    def panel(self, strategy, cases, worst_case_weight=0.5) -> dict:
        if self.simulation_budget is not None:
            self.simulation_budget.require(sum(case.games for case in cases))
        results = [self.evaluate(strategy, case) for case in cases]
        return {
            "score": aggregate_fitness([r["win_rate"] for r in results],
                                       worst_case_weight=worst_case_weight),
            "matchups": results,
        }


class DominionGEPAAdapter:
    propose_new_texts = None

    def __init__(self, evaluator: MatchupEvaluator, *, schema_version=None):
        self.evaluator = evaluator
        self.schema_version = schema_version
        self.invalid_candidates = 0

    def evaluate(self, batch, candidate, capture_traces=False):
        from gepa.core.adapter import EvaluationBatch

        try:
            if set(candidate) != {"strategy"}:
                raise ValueError("Expected exactly one component named strategy")
            strategy = compile_genome(candidate["strategy"], self.evaluator.info)
            if (self.schema_version is not None
                    and json.loads(candidate["strategy"])["schema_version"] != self.schema_version):
                raise ValueError("Candidate must preserve the experiment's schema_version")
        except ValueError as exc:
            self.invalid_candidates += 1
            outputs = [{"case": asdict(case), "error": str(exc)} for case in batch]
            return EvaluationBatch(outputs, [-1.0] * len(batch),
                                   outputs if capture_traces else None)
        outputs = [self.evaluator.evaluate(strategy, case, trace=capture_traces) for case in batch]
        return EvaluationBatch(outputs, [r["win_rate"] for r in outputs],
                               outputs if capture_traces else None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        capabilities = {name: asdict(caps) for name, caps in
                        kingdom_capabilities(self.evaluator.board.kingdom_cards).items()}
        return {component: [{
            "Inputs": {
                "board": asdict(self.evaluator.board), "card_capabilities": capabilities,
                "contract": (
                    "Return ONLY a JSON object preserving schema_version and every genome field. "
                    "Change copy counts, ordered targets, turn windows, dependencies, economy, "
                    "greening, and play order together when useful. Card names must be in this board "
                    "or its basic supply. Copies: 1..10; turns: 1..100; pile thresholds: 0..12. "
                    "The compiler puts openings first, then before_province targets BEFORE Colony "
                    "and Province, then before_duchy targets, Duchy, Estate, build targets, Platinum, "
                    "Gold, before_silver targets, Silver, fallback targets. Schema 2 supports Colony "
                    "multi_buy gates (current coins and buys, commits after first Colony, or fallback turn), "
                    "colony_or_turn Province gates, only_first_gain openings, counted dependencies, "
                    "and deck balancing (own target count minus balance_card count <= balance_max_lead). "
                    "treasure_reserve holds its Treasure while its gainer is in play and a listed "
                    "gain target is below cap with supply remaining. tactics can balance Anvil gains "
                    "by current count / target copies (ties follow offered order), and protect Action "
                    "multipliers before the last other Action in the main Action phase. Schema 1 "
                    "retains only the older fields and unconditional Colony rule. "
                    "Action and Treasure orders contain only cards of their respective roles. "
                    "Target order within each priority band matters. No code or new fields. "
                    "Aim for wins across strong opponents, not score margin alone. "
                    "The representative loss is evidence of behavior, not proof of its cause."
                ),
            },
            "Generated Outputs": candidate[component],
            "Feedback": trace,
        } for trace in eval_batch.trajectories or []] for component in components_to_update}


class FailFastReflection:
    """GEPA catches proposer errors; remember provider errors and stop the run."""

    def __init__(self, lm):
        self.lm = lm
        self.failure = None

    @property
    def total_cost(self):
        return getattr(self.lm, "total_cost", 0.0)

    @property
    def total_tokens_in(self):
        return getattr(self.lm, "total_tokens_in", 0)

    @property
    def total_tokens_out(self):
        return getattr(self.lm, "total_tokens_out", 0)

    def __call__(self, prompt):
        if self.failure is not None:
            raise RuntimeError("Reflection provider failed earlier") from self.failure
        try:
            return self.lm(prompt)
        except Exception as exc:
            self.failure = exc
            raise

    def check(self):
        if self.failure is not None:
            raise RuntimeError("Reflection provider failed; experiment has no valid result") from self.failure


def optimize_strategy(evaluator, seed_text, train_cases, validation_cases, *,
                      reflection_lm, max_metric_calls, run_dir, seed=0,
                      max_reflection_cost=None):
    """GEPA proposes seeds; robust selection never sees held-out test games."""
    try:
        import gepa
    except ImportError as exc:
        raise RuntimeError("Install optional dependencies with python -m pip install -e '.[gepa]'") from exc
    parse_genome(seed_text, evaluator.info)
    iteration_budget = 2 + len(validation_cases)
    if max_metric_calls < len(validation_cases) + iteration_budget:
        raise ValueError("Metric budget must cover initial validation and one fully validated proposal")
    if {c.split for c in train_cases} != {"train"} or {c.split for c in validation_cases} != {"validation"}:
        raise ValueError("GEPA may only receive training and validation cases")
    adapter = DominionGEPAAdapter(evaluator, schema_version=json.loads(seed_text)["schema_version"])
    reflection = FailFastReflection(reflection_lm)

    def stop(state):
        reflection.check()
        # GEPA's built-in budget is checked between iterations. Reserve enough
        # for parent/child screens AND a full panel so this is a hard call cap.
        return state.total_num_evals + iteration_budget > max_metric_calls

    result = gepa.optimize(
        seed_candidate={"strategy": seed_text}, trainset=train_cases,
        valset=validation_cases, adapter=adapter, reflection_lm=reflection,
        reflection_prompt_template=STRATEGY_REFLECTION_PROMPT,
        reflection_minibatch_size=1, skip_perfect_score=False,
        max_metric_calls=max_metric_calls, run_dir=str(run_dir), seed=seed,
        max_reflection_cost=max_reflection_cost,
        stop_callbacks=[stop],
        raise_on_exception=True,
    )
    reflection.check()
    # GEPA's frontier uses per-case win rates. Its default best_idx is a mean;
    # the seed we inject instead follows the league's worst-tail objective.
    robust_scores = [aggregate_fitness(list(scores.values()), worst_case_weight=0.5)
                     if len(scores) == len(validation_cases) else float("-inf")
                     for scores in result.val_subscores]
    best = max(range(len(robust_scores)), key=robust_scores.__getitem__)
    return result.candidates[best]["strategy"], {
        "selected_index": best, "robust_validation_scores": robust_scores,
        "invalid_candidates": adapter.invalid_candidates,
        "result": result.to_dict(),
    }
