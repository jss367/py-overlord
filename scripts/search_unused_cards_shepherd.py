"""Reproducible search and seat-balanced comparisons for the random kingdom."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import random
import time

from dominion.ai.genetic_ai import GeneticAI
from dominion.allies.registry import get_ally
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.unused_cards_shepherd import UnusedCardsShepherd


BOARD = load_board("boards/random_unused_card_kingdom.txt")
MONEY = dict(
    shepherd=0, village=0, draw=0, bauble=0, silvers=99, golds=99, opening="Silver"
)
PANEL = [
    MONEY,
    dict(MONEY, draw=2, opening="Silver"),
    dict(shepherd=4, village=2, draw=3, green=8, estates=6),
    dict(shepherd=2, village=2, draw=3, university=2, green=8),
]


def match(task):
    a, b, games, seed = task
    wins = ties = truncated = 0
    turns = 0
    scores = [0, 0]
    decks = [Counter(), Counter()]
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(UnusedCardsShepherd(**a)), GeneticAI(UnusedCardsShepherd(**b))]
        if i % 2:
            ais.reverse()
        s = GameState(players=[], supply={})
        s.log_callback = lambda *_: None
        s.initialize_game(
            ais,
            [get_card(n) for n in BOARD.kingdom_cards],
            allies=[get_ally(n) for n in BOARD.allies],
        )
        while not s.is_game_over() and s.turn_number < 160:
            s.play_turn()
        truncated += not s._normal_game_end_reached()
        players = s.players if i % 2 == 0 else list(reversed(s.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        wins += keys[0] > keys[1]
        ties += keys[0] == keys[1]
        turns += s.turn_number
        for j, player in enumerate(players):
            scores[j] += keys[j][0]
            decks[j].update(c.name for c in player.all_cards())
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        wins=wins,
        ties=ties,
        rate=(wins + ties / 2) / games,
        turns=turns / games,
        scores=[x / games for x in scores],
        truncated=truncated,
        decks=[{k: round(v / games, 3) for k, v in sorted(d.items())} for d in decks],
    )


def candidates():
    candidates = list(PANEL)
    # Explicitly include single-card money, Shepherd, Copper-heavy, Forts,
    # University, and diverse Fairgrounds theories before random tuning.
    for draw in [1, 2, 3]:
        candidates += [dict(MONEY, draw=draw), dict(MONEY, embassy=draw)]
    for shepherd, estates in itertools.product([2, 4, 6], [0, 6, 10]):
        candidates.append(dict(shepherd=shepherd, village=1, draw=1, estates=estates))
    for counting, village in itertools.product([1, 2, 4], [0, 2]):
        candidates.append(dict(MONEY, counting=counting, village=village, bauble=2))
    rng = random.Random(20260908)
    for _ in range(100):
        candidates.append(
            dict(
                shepherd=rng.choice([0, 1, 2, 3, 4, 6]),
                village=rng.choice([0, 1, 2, 3, 4]),
                draw=rng.choice([0, 1, 2, 3, 4, 5]),
                embassy=rng.choice([0, 0, 1, 2]),
                university=rng.choice([0, 0, 0, 1, 2]),
                counting=rng.choice([0, 0, 0, 1]),
                bauble=rng.choice([0, 1, 2]),
                fish=rng.choice([0, 0, 1]),
                silvers=rng.choice([1, 2, 3]),
                golds=rng.choice([1, 2, 3, 4]),
                green=rng.choice([0, 6, 8, 10, 12]),
                estates=rng.choice([0, 0, 6, 8]),
                fairgrounds=rng.choice([False, False, True]),
                forts=rng.choice([False, False, True]),
                opening=rng.choice(["Shepherd", "Silver", "Tent"]),
                duchy=rng.choice([2, 3, 4]),
            )
        )
    return candidates


def run(tasks, path, workers):
    start = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(match, tasks):
            results.append(result)
            if len(results) % 20 == 0:
                print(
                    f"{len(results)}/{len(tasks)} matches, {time.monotonic() - start:.1f}s",
                    flush=True,
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")
    return results


def ranking(results):
    totals, counts, specs = Counter(), Counter(), {}
    for r in results:
        for side, score in [("a", r["rate"]), ("b", 1 - r["rate"])]:
            key = json.dumps(r[side], sort_keys=True)
            totals[key] += score
            counts[key] += 1
            specs[key] = r[side]
    return [
        (totals[k] / counts[k], specs[k])
        for k in sorted(totals, key=lambda k: -totals[k] / counts[k])
    ]


def screening_ranking(results):
    totals, counts, specs = Counter(), Counter(), {}
    for result in results:
        key = json.dumps(result["a"], sort_keys=True)
        totals[key] += result["rate"]
        counts[key] += 1
        specs[key] = result["a"]
    return [
        (totals[k] / counts[k], specs[k])
        for k in sorted(totals, key=lambda k: -totals[k] / counts[k])
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=["smoke", "search", "refine", "tournament", "validation"]
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path(".context/unused-cards-search.json")
    )
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.mode == "smoke":
        print(json.dumps(match(({}, MONEY, 8, 100)), indent=2))
        return
    if args.mode == "search":
        tasks = [
            (a, b, 40, 1000 + 100 * i + 20 * j)
            for i, a in enumerate(candidates())
            for j, b in enumerate(PANEL)
        ]
    elif args.mode == "refine":
        previous = screening_ranking(json.loads(args.input.read_text()))
        refined = [
            dict(
                MONEY,
                draw=draw,
                embassy=embassy,
                village=village,
                shepherd=shepherd,
                bauble=bauble,
            )
            for draw, embassy, village, shepherd, bauble in itertools.product(
                [0, 1, 2], [0, 1], [0, 1], [0, 1], [0, 1]
            )
        ]
        # Retain the strongest two substantial engines from the broad screen.
        refined += [p for _, p in previous if p.get("shepherd", 3) >= 2][:2]
        panel = [MONEY, dict(MONEY, embassy=1), dict(MONEY, draw=1)]
        tasks = [
            (a, b, 24, 30000 + 100 * i + 20 * j)
            for i, a in enumerate(refined)
            for j, b in enumerate(panel)
        ]
    elif args.mode == "tournament":
        previous = json.loads(args.input.read_text())
        ordered = screening_ranking(previous)
        finalists = [p for _, p in ordered[:6]]
        # Also test buying the core immediately on a $5 opening rather
        # than committing the first buy to Silver.
        for _, spec in ordered[:2]:
            opening = next(
                (
                    name
                    for name, key in [
                        ("Cursed Village", "village"),
                        ("Catacombs", "draw"),
                        ("Embassy", "embassy"),
                        ("Shepherd", "shepherd"),
                    ]
                    if spec.get(key, 0)
                ),
                "Silver",
            )
            variant = dict(spec, opening=opening)
            if variant not in finalists:
                finalists.append(variant)
        for _, spec in ordered[6:]:
            if len(finalists) >= 8:
                break
            if spec not in finalists:
                finalists.append(spec)
        tasks = [
            (a, b, 200, 50000 + 500 * i)
            for i, (a, b) in enumerate(itertools.combinations(finalists, 2))
        ]
    else:
        previous = json.loads(args.input.read_text())
        ordered = ranking(previous)
        champion = ordered[0][1]
        opponents = [p for _, p in ordered[1:5]] + PANEL[:2]
        tasks = [(champion, b, 400, 200000 + 1000 * i) for i, b in enumerate(opponents)]
    results = run(tasks, args.output, args.workers)
    print(
        "Games:",
        sum(r["games"] for r in results),
        "Truncated:",
        sum(r["truncated"] for r in results),
    )
    if args.mode in {"search", "refine"}:
        print(json.dumps(screening_ranking(results)[:8], indent=2))
    elif args.mode == "tournament":
        print(json.dumps(ranking(results)[:8], indent=2))
    else:
        print(
            json.dumps(
                [
                    {key: result[key] for key in ("b", "games", "wins", "ties", "rate")}
                    for result in results
                ],
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
