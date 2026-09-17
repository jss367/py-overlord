"""Reproduce candidate screening, finalist tournaments, and held-out validation.

Run from the repository root with PYTHONPATH=. Python's random seed controls
both opening shuffles and later draws. Each seed is played in both seats.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import random
import time

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.three_unused_kingdoms import (
    KINGDOMS,
    UnusedKingdomPolicy,
)


DATA = Path("scripts/data/three_unused_kingdoms")


def anchors(board):
    if board == "sentry_hunting_party":
        return [
            {},
            dict(targets=[["Hunting Party", 2]]),
            dict(
                targets=[
                    ["Sentry", 1],
                    ["Hunting Party", 5],
                    ["Merchant", 3],
                    ["Candlestick Maker", 1],
                ],
                silver=3,
            ),
            dict(
                targets=[
                    ["Sentry", 1],
                    ["Bazaar", 2],
                    ["Conspirator", 5],
                    ["Hunting Party", 4],
                    ["Candlestick Maker", 1],
                ],
                silver=2,
                green=10,
            ),
        ]
    if board == "minion_courtier":
        return [
            {},
            dict(targets=[["Courtier", 2], ["Diplomat", 1]]),
            dict(
                targets=[["Minion", 10], ["Baron", 1]],
                silver=2,
                gold=0,
                opening="Baron",
            ),
            dict(
                targets=[
                    ["Trading Post", 1],
                    ["Minion", 8],
                    ["Conclave", 2],
                    ["Shanty Town", 2],
                ],
                silver=2,
                gold=0,
                green=10,
            ),
        ]
    return [
        {},
        dict(targets=[["Old Witch", 2]]),
        dict(
            targets=[
                ["Old Witch", 1],
                ["Recruiter", 1],
                ["Rabble", 2],
                ["Silk Merchant", 3],
                ["Squire", 2],
            ],
            silver=3,
        ),
        dict(targets=[["Soothsayer", 2], ["Spices", 3]]),
    ]


def candidates(board):
    rng = random.Random(20260917 + list(KINGDOMS).index(board))
    specs = anchors(board)
    # Test each of the ten piles as the sole kingdom addition to money.
    for name in KINGDOMS[board]:
        for cap in (1, 2, 5):
            specs.append(dict(targets=[[name, cap]], opening=name))
    # Tune all archetypes, then test independently sampled mixed plans.
    for i in range(120):
        if i < 70:
            spec = dict(rng.choice(anchors(board)[1:]))
            targets = [
                [name, rng.choice([1, 2, 3, 5, 8])]
                for name, _ in spec.get("targets", [])
                if rng.random() < 0.9
            ]
        else:
            spec = {}
            names = rng.sample(list(KINGDOMS[board]), rng.randint(2, 6))
            targets = [[name, rng.choice([1, 1, 2, 3, 5])] for name in names]
        if rng.random() < 0.5:
            rng.shuffle(targets)
        spec.update(
            targets=targets,
            silver=rng.choice([2, 3, 5, 99]),
            gold=rng.choice([0, 2, 4, 99]),
            green=rng.choice([0, 8, 10, 12]),
            duchy=rng.choice([2, 3, 4]),
            opening=rng.choice(["Silver", *[n for n, _ in targets]]),
            minion_redraw=rng.choice([1, 2, 3, 4]),
            attack_first=rng.choice([True, False]),
        )
        specs.append(spec)
    return list({json.dumps(p, sort_keys=True): p for p in specs}.values())


def match(task):
    board, a, b, games, seed = task
    if games <= 0 or games % 2:
        raise ValueError("Seat-balanced matches require a positive even game count")
    config = load_board(f"boards/{board}.txt")
    wins = ties = truncated = turns = 0
    scores = [0, 0]
    decks = [Counter(), Counter()]
    pair_points = []
    points = 0
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(UnusedKingdomPolicy(board, **p)) for p in (a, b)]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(ais, [get_card(n) for n in config.kingdom_cards])
        while not state.is_game_over() and state.turn_number < 160:
            state.play_turn()
        truncated += not state._normal_game_end_reached()
        players = state.players if i % 2 == 0 else list(reversed(state.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        win, tie = keys[0] > keys[1], keys[0] == keys[1]
        wins += win
        ties += tie
        points += win + tie / 2
        if i % 2:
            pair_points.append(points / 2)
            points = 0
        turns += state.turn_number
        for j, player in enumerate(players):
            scores[j] += keys[j][0]
            decks[j].update(c.name for c in player.all_cards())
    return dict(
        board=board,
        a=a,
        b=b,
        games=games,
        seed=seed,
        wins=wins,
        ties=ties,
        rate=(wins + ties / 2) / games,
        pair_points=pair_points,
        turns=turns / games,
        scores=[x / games for x in scores],
        truncated=truncated,
        decks=[{n: round(v / games, 3) for n, v in sorted(d.items())} for d in decks],
    )


def ranking(results, screening=False):
    points, counts, specs = Counter(), Counter(), {}
    for r in results:
        sides = (
            [("a", r["rate"])]
            if screening
            else [("a", r["rate"]), ("b", 1 - r["rate"])]
        )
        for side, rate in sides:
            key = json.dumps(r[side], sort_keys=True)
            points[key] += rate
            counts[key] += 1
            specs[key] = r[side]
    return [
        (points[k] / counts[k], specs[k])
        for k in sorted(points, key=lambda k: (-points[k] / counts[k], k))
    ]


def run(tasks, path, workers):
    start = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(match, tasks):
            results.append(result)
            if len(results) % 50 == 0:
                print(
                    f"{path.stem}: {len(results)}/{len(tasks)}, {time.monotonic() - start:.1f}s",
                    flush=True,
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")
    print(
        f"{path}: {sum(r['games'] for r in results)} games; "
        f"{sum(r['truncated'] for r in results)} truncated",
        flush=True,
    )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["smoke", "screen", "tournament", "validate"])
    parser.add_argument("--board", choices=list(KINGDOMS), required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, default=DATA)
    args = parser.parse_args()
    board = args.board
    prefix = args.output_dir / board
    if args.mode == "smoke":
        print(json.dumps(match((board, anchors(board)[2], {}, 8, 100)), indent=2))
        return
    if args.mode == "screen":
        tasks = [
            (board, a, b, 40, 10000 + 100 * i + 30 * j)
            for i, a in enumerate(candidates(board))
            for j, b in enumerate(anchors(board))
        ]
    elif args.mode == "tournament":
        rows = json.loads(prefix.with_name(board + "_screen.json").read_text())
        finalists = [p for _, p in ranking(rows, screening=True)[:8]]
        tasks = [
            (board, a, b, 240, 100000 + 200 * i)
            for i, (a, b) in enumerate(itertools.combinations(finalists, 2))
        ]
    else:
        rows = json.loads(prefix.with_name(board + "_tournament.json").read_text())
        ranked = ranking(rows)
        champion = ranked[0][1]
        opponents = [p for _, p in ranked[1:5]] + anchors(board)[:2]
        tasks = [
            (board, champion, b, 1000, 1000000 + 2000 * i)
            for i, b in enumerate(opponents)
        ]
    rows = run(tasks, prefix.with_name(board + "_" + args.mode + ".json"), args.workers)
    if args.mode != "validate":
        print(json.dumps(ranking(rows, screening=args.mode == "screen")[:8], indent=2))
    else:
        print(
            json.dumps(
                [{k: r[k] for k in ("rate", "wins", "ties", "b")} for r in rows],
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
