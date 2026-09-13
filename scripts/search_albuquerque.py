"""Round-robin and confirmation matches for the Albuquerque board.

Run from the repository root with PYTHONPATH=. Strategies are loader names
(``StrategyLoader``) or paths to ``*.py`` champion files. Each shuffle seed is
played from both seats; ties earn half a win.

    python scripts/search_albuquerque.py --strategies "Big Money" \
        "Albuquerque Chapel Bridge Engine" --games 200
    python scripts/search_albuquerque.py --strategies A B C --games 400 \
        --output docs/analysis/albuquerque_round_robin.json
"""

import argparse
import importlib.util
import itertools
import json
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategy_loader import StrategyLoader

BOARD = load_board("boards/albuquerque.txt")
_LOADER = None


def make(ref: str) -> EnhancedStrategy:
    """Resolve a strategy ref: ``variant:{json}`` builds a Bridge-engine
    variant from ``albuquerque_seeds._engine_gains`` keyword arguments (plus
    optional ``"multiplier_first"`` and ``"name"``); ``*.py`` loads a
    champion file; anything else is a ``StrategyLoader`` name."""
    global _LOADER
    if ref.startswith("variant:"):
        from dominion.strategy.strategies.albuquerque_seeds import _BridgeEngine

        spec = json.loads(ref[len("variant:"):])
        opener = spec.pop("opener", "Masquerade")
        first = spec.pop("multiplier_first", "Bridge")
        name = spec.pop("name", ref)

        class Variant(_BridgeEngine):
            pass

        Variant.opener = opener
        Variant.gain_kwargs = spec
        Variant.multiplier_first = first
        strategy = Variant()
        strategy.name = name
        return strategy
    if ref.endswith(".py"):
        spec = importlib.util.spec_from_file_location(Path(ref).stem, ref)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in dir(module):
            if name.startswith("create_"):
                return getattr(module, name)()
        raise ValueError(f"No create_* factory in {ref}")
    if _LOADER is None:
        _LOADER = StrategyLoader()
    strategy = _LOADER.get_strategy(ref)
    if strategy is None:
        raise ValueError(f"Unknown strategy {ref!r}")
    return strategy


def play_game(a: str, b: str, seed: int, swap: bool):
    random.seed(seed)
    ais = [GeneticAI(make(a)), GeneticAI(make(b))]
    if swap:
        ais.reverse()
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(ais, [get_card(n) for n in BOARD.kingdom_cards])
    while not state.is_game_over() and state.turn_number < 160:
        state.play_turn()
    players = list(reversed(state.players)) if swap else state.players
    keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
    win = 1.0 if keys[0] > keys[1] else 0.5 if keys[0] == keys[1] else 0.0
    return win, state.turn_number, [k[0] for k in keys], not state._normal_game_end_reached()


def match(task):
    a, b, games, seed = task
    score = ties = truncated = 0
    turns = 0
    vps = [0, 0]
    for i in range(games):
        win, length, scores, trunc = play_game(a, b, seed + i // 2, bool(i % 2))
        score += win
        ties += win == 0.5
        truncated += trunc
        turns += length
        vps[0] += scores[0]
        vps[1] += scores[1]
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        rate=score / games,
        ties=ties,
        turns=turns / games,
        scores=[v / games for v in vps],
        truncated=truncated,
    )


def run(tasks, workers):
    start = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(match, tasks):
            results.append(r)
            print(
                f"{len(results)}/{len(tasks)} {r['a']} vs {r['b']}: "
                f"{100 * r['rate']:.1f}%  ({time.time() - start:.0f}s)",
                flush=True,
            )
    return results


def matrix(strategies, results):
    rate = {}
    for r in results:
        rate[(r["a"], r["b"])] = r["rate"]
        rate[(r["b"], r["a"])] = 1 - r["rate"]
    rows = []
    for a in strategies:
        others = [rate[(a, b)] for b in strategies if b != a]
        rows.append((sum(others) / len(others), a))
    rows.sort(reverse=True)
    print()
    print(f"{'strategy':45s} avg   " + " ".join(f"{i + 1:>5d}" for i in range(len(strategies))))
    order = [a for _, a in rows]
    for i, (avg, a) in enumerate(rows):
        cells = " ".join(
            f"{100 * rate[(a, b)]:5.0f}" if b != a else "    -" for b in order
        )
        print(f"{i + 1:2d}. {a[:41]:41s} {100 * avg:5.1f} {cells}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategies", nargs="+", required=True)
    parser.add_argument("--versus", nargs="*", default=None,
                        help="If given, play every --strategies entry against every --versus entry instead of a round robin.")
    parser.add_argument("--games", type=int, default=200,
                        help="Games per pairing; a positive even number, since each shuffle seed is played from both seats.")
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.games <= 0 or args.games % 2:
        parser.error(f"--games must be a positive even number (each seed is played from both seats), got {args.games}")
    if not args.versus and len(args.strategies) < 2:
        parser.error("a round robin needs at least two --strategies (or pass --versus)")
    if args.versus:
        pairs = [(a, b) for a in args.strategies for b in args.versus]
    else:
        pairs = list(itertools.combinations(args.strategies, 2))
    tasks = [(a, b, args.games, args.seed + 1000 * i) for i, (a, b) in enumerate(pairs)]
    results = run(tasks, args.workers)
    if not args.versus:
        matrix(args.strategies, results)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n")
    if any(r["truncated"] for r in results):
        print("WARNING: turn-limit truncations occurred")


if __name__ == "__main__":
    main()
