"""Seat-balanced search using the exact ten-card Lucky Coin / five Ruins start."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
import json
from pathlib import Path
import random
import time

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.prophecies.registry import get_prophecy
from generated_strategies.lucky_coin_ruins import KINGDOM, START, LuckyCoinRuins


def make_strategy(spec):
    settings = dict(spec)
    if "cleanup" in settings:
        from generated_strategies.lucky_coin_cleanup import LuckyCoinCleanup

        return LuckyCoinCleanup(**settings)
    return LuckyCoinRuins(**settings)


def setup(a, b, seed, swap=False, *, state_class=GameState):
    random.seed(seed)
    ais = [GeneticAI(make_strategy(a)), GeneticAI(make_strategy(b))]
    if swap:
        ais.reverse()
    s = state_class(players=[], supply={})
    s.log_callback = lambda *_: None
    s.initialize_game(
        ais,
        [get_card(n) for n in KINGDOM],
        events=[get_event("Banquet"), get_event("Scrounge")],
        prophecy=get_prophecy("Kind Emperor"),
    )
    # Scenario setup, not gains: keep normal Kingdom and eight-Province piles.
    s.supply["Copper"] = 60 - 8
    for p in s.players:
        p.hand = []
        p.discard = []
        p.deck = [get_card(n) for n in START]
        random.shuffle(p.deck)
        p.draw_cards(5)
    return s


def match(task):
    a, b, games, seed = task
    vals, lengths, scores, decks = [], [], [], []
    truncated = 0
    for i in range(games):
        s = setup(a, b, seed + i // 2, bool(i % 2))
        while not s.is_game_over() and s.turn_number < 160:
            s.play_turn()
        truncated += not s._normal_game_end_reached()
        ps = list(reversed(s.players)) if i % 2 else s.players
        keys = [(p.get_victory_points(), -p.turns_taken) for p in ps]
        vals.append(1.0 if keys[0] > keys[1] else 0.5 if keys[0] == keys[1] else 0.0)
        scores.append([k[0] for k in keys])
        lengths.append(s.turn_number)
        decks.append(Counter(x.name for x in ps[0].all_cards()))
    pairs = [(vals[i] + vals[i + 1]) / 2 for i in range(0, games, 2)]
    rate = sum(vals) / games
    se = (
        (sum((x - rate) ** 2 for x in pairs) / (len(pairs) - 1) / len(pairs)) ** 0.5
        if len(pairs) > 1
        else 0
    )
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        rate=rate,
        ci95=[max(0, rate - 1.96 * se), min(1, rate + 1.96 * se)],
        seed_pairs=len(pairs),
        pair_score_sum_squares=sum(x * x for x in pairs),
        wins=vals.count(1),
        ties=vals.count(0.5),
        truncated=truncated,
        turns=sum(lengths) / games,
        scores=[sum(x[j] for x in scores) / games for j in (0, 1)],
        deck={n: sum(d[n] for d in decks) / games for n in sorted(set().union(*decks))},
    )


def run(tasks, output, workers):
    results = []
    start = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(match, tasks):
            results.append(r)
            if len(results) % 10 == 0:
                print(
                    f"{len(results)}/{len(tasks)} matchups in {time.time() - start:.1f}s",
                    flush=True,
                )
    Path(output).write_text(json.dumps(results, indent=2) + "\n")
    if any(r["truncated"] for r in results):
        raise RuntimeError("Truncated games; inspect before interpreting results")
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "mode", choices=["screen", "refine", "finalists", "validate", "smoke"]
    )
    ap.add_argument("--specs", type=Path)
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=10000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    if args.games < 2 or args.games % 2:
        ap.error("--games must be positive and even")
    if args.specs:
        specs = json.loads(args.specs.read_text())
    else:
        specs = [{}]
    if args.mode == "screen":
        specs = []
        for opening in [
            "Secluded Shrine",
            "Banquet",
            "Change",
            "Spice Merchant",
            "Fool",
            "Battle Plan",
            "Silver",
            "Daimyo",
        ]:
            for free in ["adaptive", "tea", "daimyo", "draw"]:
                specs.append(dict(opening=opening, free=free))
        specs += [
            dict(shrine=0),
            dict(shrine=2),
            dict(lost=0, mining=0),
            dict(change=1),
            dict(spice=1),
            dict(highway=1),
            dict(mining=0),
            dict(battle=1, warlord=1),
            dict(money=True),
            dict(money=True, highway=1),
        ]
    if args.mode in ("screen", "refine"):
        opponents = [{}, dict(money=True), dict(change=1), dict(highway=1)]
        tasks = [
            (a, b, args.games, args.seed + 1000 * j)
            for a in specs
            for j, b in enumerate(opponents)
            if a != b
        ]
    elif args.mode == "finalists":
        tasks = [
            (a, b, args.games, args.seed + 1000 * i)
            for i, (a, b) in enumerate(combinations(specs, 2))
        ]
    elif args.mode == "validate":
        tasks = [
            (specs[0], b, args.games, args.seed + 2000 * i)
            for i, b in enumerate(specs[1:])
        ]
    else:
        tasks = [(specs[0], dict(money=True), args.games, args.seed)]
    results = run(tasks, args.output, args.workers)
    ranks = []
    for a in specs:
        rates = [
            r["rate"] if r["a"] == a else 1 - r["rate"]
            for r in results
            if r["a"] == a or (args.mode == "finalists" and r["b"] == a)
        ]
        if rates:
            ranks.append((sum(rates) / len(rates), a))
    for rate, a in sorted(ranks, key=lambda x: -x[0])[:20]:
        print(f"{rate:.3f} {a}")


if __name__ == "__main__":
    main()
