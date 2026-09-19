"""Reproducible, seat-balanced search on the Hunting Grounds / Ghost Ship board."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import random
import statistics
import time

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.hunting_grounds_ghost_ship import (
    KINGDOM,
    HuntingGroundsPolicy,
)

DATA = Path("scripts/data/hunting_grounds_ghost_ship")


def anchors():
    return [
        {},
        dict(targets=[["Ghost Ship", 2]]),
        dict(targets=[["Hunting Grounds", 2]]),
        dict(
            targets=[
                ["Raze", 1],
                ["Apprentice", 1],
                ["Ghost Ship", 1],
                ["Hunting Grounds", 3],
                ["Woodcutter", 1],
            ],
            village_ratio=1,
            silver=3,
            green=10,
        ),
        dict(
            targets=[["Bishop", 1], ["Hunting Grounds", 3], ["Woodcutter", 1]],
            village_ratio=1,
            bishop_fodder=True,
            silver=4,
        ),
    ]


def candidates():
    rng = random.Random(20260919)
    specs = anchors()
    for n in KINGDOM:
        for cap in (1, 2, 4):
            specs.append(dict(targets=[[n, cap]], opening=n))
    for i in range(110):
        if i < 70:
            p = dict(rng.choice(anchors()[1:]))
            targets = [
                [n, rng.choice([1, 2, 3, 4])]
                for n, _ in p["targets"]
                if rng.random() < 0.9
            ]
        else:
            p = {}
            targets = [
                [n, rng.choice([1, 1, 2, 3])]
                for n in rng.sample(list(KINGDOM), rng.randint(2, 6))
            ]
        rng.shuffle(targets)
        p.update(
            targets=targets,
            opening=rng.choice(
                ["Silver", "Raze", "Ghost Ship", *[n for n, _ in targets]]
            ),
            village_ratio=rng.choice([0, 0.5, 1]),
            silver=rng.choice([2, 3, 5, 99]),
            gold=rng.choice([2, 4, 99]),
            green=rng.choice([0, 8, 10, 12]),
            duchy=rng.choice([2, 3, 4]),
            copper_floor=rng.choice([0, 2, 4]),
            bishop_fodder=rng.choice([False, True]),
            draw_first=rng.choice([False, True]),
        )
        specs.append(p)
    return list({json.dumps(p, sort_keys=True): p for p in specs}.values())


def match(task):
    a, b, games, seed = task
    if games <= 0 or games % 2:
        raise ValueError("Use a positive even game count")
    wins = ties = truncated = turns = 0
    scores = [0, 0]
    decks = [Counter(), Counter()]
    pairs = []
    pair = 0
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(HuntingGroundsPolicy(**p)) for p in (a, b)]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(ais, [get_card(n) for n in KINGDOM])
        while not state.is_game_over() and state.turn_number < 160:
            state.play_turn()
        truncated += not state._normal_game_end_reached()
        players = state.players if i % 2 == 0 else list(reversed(state.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        win, tie = keys[0] > keys[1], keys[0] == keys[1]
        wins += win
        ties += tie
        pair += win + tie / 2
        if i % 2:
            pairs.append(pair / 2)
            pair = 0
        turns += state.turn_number
        for j, player in enumerate(players):
            scores[j] += keys[j][0]
            decks[j].update(c.name for c in player.all_cards())
    rate = (wins + ties / 2) / games
    error = 1.96 * statistics.stdev(pairs) / len(pairs) ** 0.5 if len(pairs) > 1 else 0
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        wins=wins,
        ties=ties,
        rate=rate,
        paired_95_interval=[max(0, rate - error), min(1, rate + error)],
        pair_points=pairs,
        turns=turns / games,
        scores=[v / games for v in scores],
        truncated=truncated,
        decks=[{n: round(v / games, 3) for n, v in sorted(d.items())} for d in decks],
    )


def ranking(rows, screen=False):
    points, counts, specs = Counter(), Counter(), {}
    invalid = {
        json.dumps(r[side], sort_keys=True)
        for r in rows
        if r["truncated"]
        for side in (["a"] if screen else ["a", "b"])
    }
    for r in rows:
        for side, rate in (
            [("a", r["rate"])] if screen else [("a", r["rate"]), ("b", 1 - r["rate"])]
        ):
            key = json.dumps(r[side], sort_keys=True)
            if key in invalid:
                continue
            points[key] += rate
            counts[key] += 1
            specs[key] = r[side]
    return [
        (points[k] / counts[k], specs[k])
        for k in sorted(points, key=lambda k: (-points[k] / counts[k], k))
    ]


def run(tasks, output, workers):
    start = time.monotonic()
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(match, tasks):
            rows.append(row)
            if len(rows) % 25 == 0:
                print(
                    f"{output.stem}: {len(rows)}/{len(tasks)} matches, {time.monotonic() - start:.1f}s",
                    flush=True,
                )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n")
    print(
        f"{sum(r['games'] for r in rows)} games, {sum(r['truncated'] for r in rows)} truncated",
        flush=True,
    )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=["smoke", "screen", "tournament", "refine", "validate"]
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, default=DATA)
    args = parser.parse_args()
    path = args.output_dir
    if args.mode == "smoke":
        print(json.dumps(match((anchors()[3], anchors()[1], 10, 100)), indent=2))
        return
    if args.mode == "screen":
        tasks = [
            (a, b, 40, 10000 + 100 * i + 20 * j)
            for i, a in enumerate(candidates())
            for j, b in enumerate(anchors())
        ]
    elif args.mode == "tournament":
        rows = json.loads((path / "screen.json").read_text())
        finalists = [p for _, p in ranking(rows, True)[:8]]
        tasks = [
            (a, b, 240, 100000 + 200 * i)
            for i, (a, b) in enumerate(itertools.combinations(finalists, 2))
        ]
    elif args.mode == "refine":
        rows = json.loads((path / "tournament.json").read_text())
        ranked = ranking(rows)
        winner = ranked[0][1]
        specs = [winner]
        for key, values in dict(
            opening=["Silver", "Raze", "Ghost Ship", "Farming Village", "Menagerie"],
            green=[0, 6, 8, 10, 12],
            silver=[2, 3, 5, 99],
            gold=[2, 4, 99],
            duchy=[2, 3, 4],
            village_ratio=[0, 0.5, 1],
            copper_floor=[0, 2, 4],
            draw_first=[False, True],
            bishop_fodder=[False, True],
        ).items():
            for v in values:
                specs.append(dict(winner, **{key: v}))
        for n in KINGDOM:
            for cap in (0, 1, 2, 4):
                targets = [
                    [name, c] for name, c in winner.get("targets", []) if name != n
                ]
                if cap:
                    targets.insert(0, [n, cap])
                specs.append(dict(winner, targets=targets))
        specs = list({json.dumps(p, sort_keys=True): p for p in specs}.values())
        opponents = [p for _, p in ranked[:3]] + anchors()[:2]
        tasks = [
            (a, b, 100, 300000 + 500 * i + 50 * j)
            for i, a in enumerate(specs)
            for j, b in enumerate(opponents)
        ]
    else:
        rows = json.loads((path / "refine.json").read_text())
        winner = ranking(rows, True)[0][1]
        top = ranking(json.loads((path / "tournament.json").read_text()))
        opponents = [p for _, p in top[:3]] + anchors() + [p for _, p in ranking(rows, True)[1:4]]
        opponents = list({json.dumps(p, sort_keys=True): p for p in opponents}.values())
        tasks = [(winner, b, 1000, 1000000 + 2000 * i) for i, b in enumerate(opponents)]
    rows = run(tasks, path / (args.mode + ".json"), args.workers)
    print(json.dumps(ranking(rows, args.mode in {"screen", "refine"})[:3], indent=2))


if __name__ == "__main__":
    main()
