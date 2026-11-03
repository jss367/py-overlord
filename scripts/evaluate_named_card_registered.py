"""Reevaluate registered policies against the prior and corrected engines.

Run this identical script in each checkout, with matching seeds and labels.
The resulting files preserve both engine fingerprints; they are compatibility
measurements, not new strategy selections or replacements for old standings.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import platform
import random

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.landmarks.registry import get_landmark
from dominion.prophecies.registry import get_prophecy
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.strategy.strategy_loader import StrategyLoader
from scripts.evaluate_named_card_decisions import HOOKS, label

WATCHED = frozenset(hook for hooks in HOOKS.values() for hook in hooks) - {"choose_trash"} | {"choose_card_to_trash"}
OPPONENTS = ("big_money_smithy", "village_smithy_lab", "chapel_witch")
TURN_LIMIT = 150


@lru_cache(maxsize=1)
def loader():
    return StrategyLoader()


def panel():
    rows = [(n, "boards/kolkata.txt") for n in loader().list_strategies() if n.startswith("Kolkata ")]
    rows += [("Recruiter Kitsune Counterfeit Money", "boards/recruiter_kitsune.txt"),
             ("Ninja Watchtower Figurine Money", "boards/stables-ninja-museum.txt"),
             ("Minion Courtier Best Found", "boards/minion_courtier.txt")]
    return rows


class ObservedAI(GeneticAI):
    def __init__(self, strategy):
        super().__init__(strategy)
        self.decisions = Counter()

    def __getattribute__(self, name):
        method = super().__getattribute__(name)
        if name not in WATCHED:
            return method
        def observed(*args, **kwargs):
            result = method(*args, **kwargs)
            self.decisions[f"{name}: {json.dumps(label(result), sort_keys=True)}"] += 1
            return result
        return observed


def run_game(strategy_name, board_path, opponent, seed, seat):
    random.seed(seed)
    ours = ObservedAI(loader().get_strategy(strategy_name))
    theirs = GeneticAI(loader().get_strategy(opponent))
    board = load_board(board_path)
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game([ours, theirs] if seat == 0 else [theirs, ours],
        [get_card(n) for n in board.kingdom_cards],
        events=[get_event(n) for n in board.events],
        landmarks=[get_landmark(n) for n in board.landmarks],
        prophecy=get_prophecy(board.prophecy) if board.prophecy else None)
    while not state.is_game_over() and state.turn_number < TURN_LIMIT:
        state.play_turn()
    us, them = state.players[seat], state.players[1 - seat]
    ranks = [(p.get_victory_points(), -p.turns_taken) for p in (us, them)]
    return {"seed": seed, "seat": seat,
        "win_share": 1 if ranks[0] > ranks[1] else 0 if ranks[0] < ranks[1] else .5,
        "score_margin": ranks[0][0] - ranks[1][0], "scores": [r[0] for r in ranks],
        "turns_taken": [us.turns_taken, them.turns_taken],
        "truncated": not state._normal_game_end_reached(), "decisions": dict(ours.decisions)}


def evaluate(task):
    name, board, rival, pairs, start = task
    records = [run_game(name, board, rival, start + offset, seat)
               for offset in range(pairs) for seat in (0, 1)]
    counts = Counter()
    for row in records:
        counts.update(row["decisions"])
    return {"strategy": name, "board": board, "opponent": rival,
            "decisions": dict(counts), "records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=20)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--engine-label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Evidence exists; choose a fresh output")
    if not 2 <= args.pairs <= 10000 or args.seed < 0 or args.workers < 1:
        parser.error("Invalid pair count, seed or workers")
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        Path(__file__), Path("scripts/evaluate_named_card_decisions.py"))}
    # Canonical path labels make the script hashes portable across checkouts.
    hashes = {"scripts/" + Path(p).name: digest for p, digest in hashes.items()}
    fingerprint = tournament_fingerprint()
    tasks = [(name, board, rival, args.pairs, args.seed + i * 10000)
        for i, (name, board, rival) in enumerate((n, b, r) for n, b in panel() for r in OPPONENTS)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = []
        for row in pool.map(evaluate, tasks):
            rows.append(row)
            print(f"{row['strategy']} / {row['opponent']}", flush=True)
    if tournament_fingerprint() != fingerprint:
        raise RuntimeError("Simulation inputs changed during evaluation")
    for p, digest in hashes.items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Runner inputs changed during evaluation")
    payload = {"engine_label": args.engine_label, "simulation_fingerprint": fingerprint,
        "runner_hashes": hashes, "python_version": platform.python_version(),
        "seed": args.seed, "pairs": args.pairs, "turn_limit": TURN_LIMIT,
        "total_games": len(rows) * args.pairs * 2,
        "limitations": "Unchanged registered policies on four declared boards versus three opponents. Matched initial seeds and both seats, but RNG streams can diverge after engine corrections. Hook counters reveal unexposed choices; unchanged results do not certify those choices. Historical standings remain unchanged.",
        "comparisons": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        output.write(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
