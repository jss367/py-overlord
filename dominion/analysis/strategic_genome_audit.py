"""Explicit reference encodings and seeded decision equivalence checks.

These hand-authored encodings are audit fixtures, never automatic search seeds.
No reference class, predicate, or decision hook is used by the compiled policy.
"""

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random

from dominion.ai.genetic_ai import GeneticAI
from dominion.simulation.reflective_strategy_search import game_seed
from dominion.simulation.strategic_genome import (
    BuildTarget, DeckTarget, EconomyPlan, GreeningPlan, OpeningTarget, StrategicGenome,
    TacticalPlan, TrashPlan, TreasureReservePlan,
)
from dominion.simulation.strategy_battle import StrategyBattle


def oslo_reference_genome(*, multi_colony=False):
    """Encode the Refined or Multi Colony reference using only public fields."""
    targets = [DeckTarget("Workers' Village", 7), DeckTarget("Magnate", 7)]
    return StrategicGenome(
        openings=[OpeningTarget("Anvil", 2, 7, only_first_gain=True)],
        build_targets=[
            BuildTarget("Bank", 2, priority_band="before_duchy"),
            BuildTarget("King's Court", 3, requires_card="Magnate", requires_copies=3,
                        priority_band="before_duchy"),
            *[BuildTarget(card, copies, priority_band="before_duchy") for card, copies in (
                ("Workers' Village", 7), ("Hoard", 1), ("Platinum", 1),
                ("Magnate", 7), ("Grand Market", 2),
            )],
        ],
        economy=EconomyPlan(buy_gold=False, prefer_platinum=False),
        greening=GreeningPlan(
            province_mode="colony_or_turn", duchy_threshold=2,
            estate_mode="threshold", estate_threshold=1,
            colony_mode="multi_buy" if multi_colony else "always",
        ),
        trash=TrashPlan(False, None, None),
        action_order=["Workers' Village", "Grand Market", "King's Court", "Magnate"],
        treasure_order=["Platinum", "Gold", "Hoard", "Silver", "Anvil", "Copper", "Bank"],
        treasure_reserve=TreasureReservePlan(targets=deepcopy(targets)),
        tactics=TacticalPlan("Anvil", targets, ["King's Court"] if multi_colony else []),
    )


def _canonical(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(_canonical(key)): _canonical(item) for key, item in value.items()}
    if hasattr(value, "name"):
        return value.name
    raise TypeError(f"Unrecorded decision output type: {type(value).__name__}")


def _record_decisions(ai, trace):
    depth = 0

    def wrap(method, name):
        def recorded(*args, **kwargs):
            nonlocal depth
            outermost = depth == 0
            depth += 1
            try:
                result = method(*args, **kwargs)
            finally:
                depth -= 1
            if outermost:
                trace.append([ai.name, name, _canonical(result)])
            return result
        return recorded

    # Record the simulator's public decision requests. Nested implementation
    # calls differ between custom hooks and generic policies and are excluded.
    for name in dir(ai):
        if name.startswith(("choose_", "should_", "select_", "decide_", "name_card_")):
            method = getattr(ai, name)
            if callable(method):
                setattr(ai, name, wrap(method, name))


def _play(battle, board, strategy, opponent, seed, seat):
    random.seed(seed)
    me, other = GeneticAI(deepcopy(strategy)), GeneticAI(deepcopy(opponent))
    me._name, other._name = "Candidate", "Opponent"
    trace = []
    _record_decisions(me, trace)
    _record_decisions(other, trace)
    first, second = (me, other) if seat == 0 else (other, me)
    game = battle.run_game(first, second, board.kingdom_cards)
    return trace, {"won": game.result_for(me) == "win", "win_share": game.win_share(me),
                   "result": game.result_for(me), "termination_reason": game.outcome.termination_reason,
                   "score": game.scores[me.name], "opponent_score": game.scores[other.name], "turns": game.turns}


def audit_equivalence(board, original, compiled, opponents, *, pairs=25, seed=1729,
                      log_dir=Path(".context/genome-audit-logs")):
    """Compare full decision sequences and outcomes under identical shuffles.

    Finite evidence, not a proof over every possible game state. Boundary
    scenarios belong in the accompanying tests.
    """
    if pairs < 1:
        raise ValueError("pairs must be positive")
    rows, decisions = [], Counter()
    saved_rng = random.getstate()
    try:
        with StrategyBattle(board_config=board, log_folder=str(log_dir), log_frequency=0) as battle:
            for opponent_index, (name, opponent) in enumerate(opponents.items()):
                for pair in range(pairs):
                    shuffle_seed = game_seed(seed, opponent_index, pair)
                    for seat in (0, 1):
                        before, outcome = _play(battle, board, original, opponent, shuffle_seed, seat)
                        after, actual = _play(battle, board, compiled, opponent, shuffle_seed, seat)
                        equal = before == after and outcome == actual
                        row = {"opponent": name, "seed": shuffle_seed, "seat": seat,
                               "equal": equal, "decisions": len(before), "outcome": outcome,
                               "trace_sha256": hashlib.sha256(json.dumps(before).encode()).hexdigest()}
                        if not equal:
                            index = next((i for i, (a, b) in enumerate(zip(before, after)) if a != b),
                                         min(len(before), len(after)))
                            row["difference"] = {"index": index, "original": before[index:index + 1],
                                                 "compiled": after[index:index + 1], "outcome": actual}
                        decisions.update(f"{actor}.{name}" for actor, name, _ in before)
                        rows.append(row)
    finally:
        random.setstate(saved_rng)
    return {"equivalent": all(row["equal"] for row in rows), "paired_games": len(rows),
            "simulated_games": 2 * len(rows), "decisions_compared": sum(decisions.values()),
            "decision_types": dict(decisions), "games": rows}
