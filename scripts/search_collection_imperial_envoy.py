"""Seeded, seat-balanced search for the Collection and Imperial Envoy kingdom."""

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
from dominion.strategy.strategies.collection_imperial_envoy import (
    CollectionImperialEnvoy,
)

BOARD = load_board("boards/collection_imperial_envoy.txt")
TURN_LIMIT = 160
MONEY = dict(
    collection=0,
    envoy=0,
    village=0,
    swindler=0,
    fish=0,
    silver=99,
    gold=99,
    green=0,
    farm=0,
    opening="Silver",
)
PANEL = [
    MONEY,
    dict(MONEY, envoy=1, first_five="Imperial Envoy"),
    dict(MONEY, swindler=1, opening="Swindler"),
    {},
    dict(collection=4, envoy=3, village=5, farm=1, green=99, gold=0),
]


def match(task):
    """Play ``games`` seat-alternating games between two parameter dicts."""
    a, b, games, seed = task
    wins = ties = truncated = 0
    turns = 0
    scores = [0, 0]
    tokens = [0, 0]
    decks = [Counter(), Counter()]
    kingdom = [get_card(name) for name in BOARD.kingdom_cards]
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [
            GeneticAI(CollectionImperialEnvoy(**a)),
            GeneticAI(CollectionImperialEnvoy(**b)),
        ]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(ais, kingdom)
        while not state.is_game_over() and state.turn_number < TURN_LIMIT:
            state.play_turn()
        truncated += not state._normal_game_end_reached()
        players = state.players if i % 2 == 0 else list(reversed(state.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        wins += keys[0] > keys[1]
        ties += keys[0] == keys[1]
        turns += state.turn_number
        for j, player in enumerate(players):
            scores[j] += keys[j][0]
            tokens[j] += player.vp_tokens
            decks[j].update(card.name for card in player.all_cards())
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        wins=wins,
        ties=ties,
        rate=(wins + ties / 2) / games,
        turns=turns / games,
        scores=[value / games for value in scores],
        tokens=[value / games for value in tokens],
        truncated=truncated,
        decks=[{k: round(v / games, 2) for k, v in sorted(d.items())} for d in decks],
    )


def candidates():
    plans = list(PANEL)
    for collection, envoy, swindler, farm in itertools.product(
        (2, 4), (1, 3), (0, 1, 2), (0, 1, 2)
    ):
        plans.append(
            dict(
                collection=collection,
                envoy=envoy,
                swindler=swindler,
                farm=farm,
                village=envoy + 1,
                green=12 if farm else 0,
            )
        )
    for seed in (1919, 2026):
        rng = random.Random(seed)
        for _ in range(60):
            plans.append(
                dict(
                    collection=rng.choice([0, 2, 3, 5]),
                    envoy=rng.choice([1, 2, 3, 4]),
                    swindler=rng.choice([0, 1, 2]),
                    village=rng.choice([0, 2, 4, 6]),
                    ghost=rng.choice([0, 0, 2, 4]),
                    sleigh=rng.choice([0, 1, 2]),
                    fish=rng.choice([0, 1, 3]),
                    mystic=rng.choice([0, 0, 1, 3]),
                    ship=rng.choice([0, 0, 1, 2]),
                    forts=rng.choice([0, 0, 1, 2, 3]),
                    silver=rng.choice([1, 2, 3, 99]),
                    gold=rng.choice([0, 2, 99]),
                    green=rng.choice([0, 8, 12, 99]),
                    farm=rng.choice([0, 1, 2, 3]),
                    opening=rng.choice(["Swindler", "Silver", "Tent", "Sleigh"]),
                    first_five=rng.choice(["Collection", "Imperial Envoy"]),
                )
            )
    return plans


def ranking(results, both=False):
    totals, counts, specs = Counter(), Counter(), {}
    for r in results:
        for side, rate in (
            [("a", r["rate"]), ("b", 1 - r["rate"])] if both else [("a", r["rate"])]
        ):
            key = json.dumps(r[side], sort_keys=True)
            totals[key] += rate
            counts[key] += 1
            specs[key] = r[side]
    return [
        (totals[k] / counts[k], specs[k])
        for k in sorted(totals, key=lambda k: -totals[k] / counts[k])
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["search", "refine", "tournament", "validate"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--games", type=int, default=40)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.games <= 0 or args.games % 2:
        parser.error("--games must be positive and even")
    if args.mode != "search" and args.input is None:
        parser.error("--input required")
    if args.mode == "search":
        tasks = [
            (a, b, args.games, 1000000 + 10000 * i + 1000 * j)
            for i, a in enumerate(candidates())
            for j, b in enumerate(PANEL)
        ]
    elif args.mode == "refine":
        ranked = ranking(json.loads(args.input.read_text()))
        leader = ranked[0][1]
        plans = [p for _, p in ranked[:12]]
        choices = dict(
            collection=[1, 2, 3, 4, 5, 6, 8],
            envoy=[0, 1, 2, 3],
            swindler=[0, 1, 2, 3],
            village=[0, 1, 2, 3, 4, 6],
            green=[0, 8, 12, 16, 99],
            farm=[0, 1, 2, 3],
            ghost=[0, 1, 2, 4],
            sleigh=[0, 1, 2],
            fish=[0, 1, 3],
            mystic=[0, 1, 2],
            ship=[0, 1, 2],
            forts=[0, 1, 2, 3],
            silver=[0, 1, 2, 99],
            gold=[0, 1, 2, 99],
            opening=["Silver", "Swindler", "Tent", "Sleigh"],
            first_five=["Collection", "Imperial Envoy"],
            cheap_first=[False, True],
        )
        for key, values in choices.items():
            plans.extend(dict(leader, **{key: value}) for value in values)
        plans = [
            json.loads(k)
            for k in dict.fromkeys(json.dumps(p, sort_keys=True) for p in plans)
        ]
        panel = [p for _, p in ranked[:4]] + PANEL[:3]
        tasks = [
            (a, b, args.games, 5000000 + 10000 * i + 1000 * j)
            for i, a in enumerate(plans)
            for j, b in enumerate(panel)
        ]
    else:
        ranked = ranking(
            json.loads(args.input.read_text()), both=args.mode == "validate"
        )
        finalists = []
        seen = set()
        for _, p in ranked:
            key = json.dumps(CollectionImperialEnvoy(**p).params, sort_keys=True)
            if key not in seen:
                finalists.append(p)
                seen.add(key)
            if len(finalists) == 10:
                break
        for p in PANEL:
            key = json.dumps(CollectionImperialEnvoy(**p).params, sort_keys=True)
            if key not in seen:
                finalists.append(p)
                seen.add(key)
        if args.mode == "tournament":
            tasks = [
                (a, b, args.games, 10000000 + 10000 * i)
                for i, (a, b) in enumerate(itertools.combinations(finalists, 2))
            ]
        else:
            winner = ranked[0][1]
            # Component removals are frozen alongside the winner before validation.
            for changes in (
                dict(collection=0, farm=0, first_five="Imperial Envoy"),
                dict(envoy=0),
                dict(ghost=0),
                dict(swindler=0, opening="Silver"),
            ):
                opponent = dict(winner, **changes)
                key = json.dumps(
                    CollectionImperialEnvoy(**opponent).params, sort_keys=True
                )
                winner_key = json.dumps(
                    CollectionImperialEnvoy(**winner).params, sort_keys=True
                )
                if key not in seen and key != winner_key:
                    finalists.append(opponent)
                    seen.add(key)
            tasks = [
                (winner, b, args.games, 20000000 + 10000 * i)
                for i, b in enumerate(finalists)
                if b != winner
            ]
    start = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(match, tasks):
            results.append(r)
            if len(results) % 50 == 0:
                print(
                    f"{len(results)}/{len(tasks)} matches; {time.monotonic() - start:.1f}s",
                    flush=True,
                )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    for rate, p in ranking(results, both=args.mode == "tournament")[:15]:
        print(round(rate, 4), json.dumps(p, sort_keys=True), flush=True)
    print(
        "games",
        sum(r["games"] for r in results),
        "truncated",
        sum(r["truncated"] for r in results),
        flush=True,
    )


if __name__ == "__main__":
    main()
