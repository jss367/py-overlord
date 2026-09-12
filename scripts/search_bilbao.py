"""Round-robin and validation matches for the Bilbao board.

Run from the repository root with ``PYTHONPATH=.``.

    python scripts/search_bilbao.py --games 100 --strategies "Bilbao Fools Gold Rush" BigMoney ...
    python scripts/search_bilbao.py --games 400 --champion "Bilbao Best Found" --strategies ...

Each shuffle seed is played in both starting seats; ties earn half a win.
Strategy references are StrategyLoader names or ``path/to/file.py`` files that
define a ``create_*()`` factory.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import importlib.util
import itertools
import json
from pathlib import Path
import random
import sys
import time

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategy_loader import StrategyLoader

BOARD_PATH = "boards/bilbao.txt"
MAX_TURNS = 120

_loader = None


def _strategy(ref: str):
    """Resolve ``ref`` to a fresh strategy instance."""
    global _loader
    if ref.endswith(".py"):
        spec = importlib.util.spec_from_file_location(Path(ref).stem, ref)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        factories = [
            getattr(module, n) for n in dir(module) if n.startswith("create_")
        ]
        if not factories:
            raise ValueError(f"No create_* factory in {ref}")
        return factories[0]()
    if _loader is None:
        _loader = StrategyLoader()
    strategy = _loader.get_strategy(ref)
    if strategy is None:
        raise ValueError(f"Unknown strategy: {ref!r}")
    return strategy


def play_game(ref_a: str, ref_b: str, seed: int, swap: bool):
    """Play one game; return (score_for_a, turns, vps, truncated)."""
    board = load_board(BOARD_PATH)
    random.seed(seed)
    ais = [GeneticAI(_strategy(ref_a)), GeneticAI(_strategy(ref_b))]
    if swap:
        ais.reverse()
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(
        ais,
        [get_card(n) for n in board.kingdom_cards],
        traits=board.traits,
    )
    while not state.is_game_over() and state.turn_number < MAX_TURNS:
        state.play_turn()
    truncated = not state._normal_game_end_reached()
    players = list(reversed(state.players)) if swap else list(state.players)
    keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
    score = 1.0 if keys[0] > keys[1] else 0.5 if keys[0] == keys[1] else 0.0
    return score, state.turn_number, [k[0] for k in keys], truncated


def match(task):
    ref_a, ref_b, games, seed = task
    total = wins = ties = truncated = 0.0
    turns = []
    vps = [0.0, 0.0]
    for i in range(games):
        score, n_turns, vp, trunc = play_game(ref_a, ref_b, seed + i // 2, bool(i % 2))
        total += score
        wins += score == 1.0
        ties += score == 0.5
        truncated += trunc
        turns.append(n_turns)
        vps[0] += vp[0]
        vps[1] += vp[1]
    return dict(
        a=ref_a,
        b=ref_b,
        games=games,
        seed=seed,
        wins=wins,
        ties=ties,
        rate=total / games,
        turns=sum(turns) / games,
        scores=[v / games for v in vps],
        truncated=truncated,
    )


def run(tasks, workers, path=None):
    """Play ``tasks`` in a process pool; survive workers killed externally."""
    from concurrent.futures.process import BrokenProcessPool

    start = time.time()
    results = []
    pending = list(tasks)
    attempts = 0
    while pending and attempts < 20:
        attempts += 1
        done_now = []
        try:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(match, task): task for task in pending}
                from concurrent.futures import as_completed

                for future in as_completed(futures):
                    result = future.result()
                    done_now.append(futures[future])
                    results.append(result)
                    print(
                        f"{len(results)}/{len(tasks)}  {result['a']} vs {result['b']}: "
                        f"{100 * result['rate']:.1f}%  ({time.time() - start:.0f}s)",
                        flush=True,
                    )
        except BrokenProcessPool:
            print("worker pool broken; retrying remaining pairings", flush=True)
        pending = [t for t in pending if t not in done_now]
    if pending:
        raise RuntimeError(f"{len(pending)} pairings never completed")
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(results, indent=2) + "\n")
    return results


def _label(ref: str) -> str:
    return Path(ref).stem if ref.endswith(".py") else ref


def print_table(names, results):
    rates = {}
    for r in results:
        rates[(r["a"], r["b"])] = r["rate"]
        rates[(r["b"], r["a"])] = 1 - r["rate"]
    width = max(len(_label(n)) for n in names)
    header = " " * (width + 2) + " ".join(f"{i + 1:>5}" for i in range(len(names)))
    print(header)
    averages = []
    for i, a in enumerate(names):
        cells = []
        vals = []
        for b in names:
            if a == b:
                cells.append("    -")
            else:
                v = rates.get((a, b))
                cells.append(f"{100 * v:5.1f}" if v is not None else "    ?")
                if v is not None:
                    vals.append(v)
        avg = sum(vals) / len(vals) if vals else 0.0
        averages.append((avg, a))
        print(f"{i + 1:>2}. {_label(a):<{width}} " + " ".join(cells) + f"   avg {100 * avg:5.1f}")
    print()
    for avg, a in sorted(averages, reverse=True):
        print(f"{100 * avg:5.1f}  {_label(a)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategies", nargs="+", required=True)
    parser.add_argument("--champion", help="Only play this strategy against --strategies.")
    parser.add_argument("--games", type=int, default=100, help="Games per pairing.")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", help="Write the JSON results here.")
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be at least 1")
    if args.games % 2:
        parser.error("--games must be even so each shuffle seed is played in both seats")
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    if args.champion:
        pairs = [(args.champion, other) for other in args.strategies if other != args.champion]
        names = [args.champion] + [s for s in args.strategies if s != args.champion]
    else:
        pairs = list(itertools.combinations(args.strategies, 2))
        names = list(args.strategies)
    tasks = [(a, b, args.games, args.seed) for a, b in pairs]
    results = run(tasks, args.workers, args.output)
    print()
    print_table(names, results)
    truncated = sum(r["truncated"] for r in results)
    if truncated:
        print(f"\n{truncated:.0f} games hit the {MAX_TURNS}-turn cap", file=sys.stderr)


if __name__ == "__main__":
    main()
