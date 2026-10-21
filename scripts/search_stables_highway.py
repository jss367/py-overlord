"""Reproduce the user-supplied Stables / Highway board search."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import random
import time

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.stables_highway import CARDS, StablesHighway

MONEY = dict()
STABLES = dict(stables=4, silver=5)
MARGRAVE = dict(margrave=1, silver=5)
DOG = dict(dog=1, silver=5)
ENGINE = dict(stables=4, highway=5, margrave=2, inn=2, silver=4, gold=3, green=10)
HUT = dict(stables=4, highway=3, margrave=1, inn=3, hut=2, weaver=2, silver=4, gold=3, green=10, order="attack")
PANEL = [MONEY, STABLES, MARGRAVE, DOG, ENGINE, HUT]


def match(task):
    a, b, games, seed = task
    wins = ties = truncated = turns = 0
    scores = [0, 0]
    outcomes = []
    decks = [Counter(), Counter()]
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(StablesHighway(**p)) for p in (a, b)]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(ais, [get_card(n) for n in CARDS])
        while not state.is_game_over() and state.turn_number < 160:
            state.play_turn()
        truncated += not state._normal_game_end_reached()
        players = state.players if i % 2 == 0 else list(reversed(state.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        wins += keys[0] > keys[1]
        ties += keys[0] == keys[1]
        outcomes.append(1.0 if keys[0] > keys[1] else 0.5 if keys[0] == keys[1] else 0.0)
        turns += state.turn_number
        for j, player in enumerate(players):
            scores[j] += keys[j][0]
            decks[j].update(c.name for c in player.all_cards())
    return dict(a=a, b=b, games=games, seed=seed, wins=wins, ties=ties,
                rate=(wins + ties / 2) / games, turns=turns / games,
                scores=[s / games for s in scores], truncated=truncated,
                pair_scores=[sum(outcomes[i:i+2]) / 2 for i in range(0, games, 2)],
                decks=[{k: round(v / games, 2) for k, v in d.items()} for d in decks])


def candidates(seed=20261020):
    named = list(PANEL)
    for stables, margrave, highway, inn in itertools.product((2, 4, 6), (0, 1, 2), (0, 3, 6), (0, 2)):
        if margrave > inn + 1:
            continue
        named.append(dict(stables=stables, margrave=margrave, highway=highway,
                          inn=inn, silver=5, gold=4, green=8))
    rng = random.Random(seed)
    for _ in range(130):
        named.append(dict(stables=rng.choice([0, 2, 3, 4, 5, 6]),
                          highway=rng.choice([0, 0, 2, 4, 6, 8]),
                          margrave=rng.choice([0, 1, 1, 2, 3]),
                          inn=rng.choice([0, 1, 2, 3, 4]),
                          hut=rng.choice([0, 0, 1, 2]),
                          weaver=rng.choice([0, 0, 1, 2]),
                          dog=rng.choice([0, 0, 1, 2]),
                          haggler=rng.choice([0, 0, 1, 2]),
                          cartographer=rng.choice([0, 0, 1, 2]),
                          develop=rng.choice([0, 0, 0, 1]),
                          silver=rng.choice([2, 4, 6, 99]), gold=rng.choice([2, 4, 99]),
                          green=rng.choice([0, 8, 10, 12, 14]), duchy=rng.choice([2, 3, 4]),
                          opening=rng.choice(["Silver", "Weaver", "Guard Dog", "Develop"]),
                          order=rng.choice(["draw", "highway", "attack"]),
                          gain_silver=rng.choice([2, 4, 6, 99])))
    return list({json.dumps(p, sort_keys=True): p for p in named}.values())


def rank(results, screen=False):
    totals, counts, specs = Counter(), Counter(), {}
    for r in results:
        for side, score in [("a", r["rate"])] + ([] if screen else [("b", 1 - r["rate"])]):
            key = json.dumps(r[side], sort_keys=True)
            specs[key] = r[side]
            totals[key] += score
            counts[key] += 1
    return [(totals[k] / counts[k], specs[k]) for k in sorted(totals, key=lambda k: -totals[k] / counts[k])]


def run(tasks, path, workers):
    start = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(match, tasks):
            results.append(result)
            if len(results) % 40 == 0:
                print(f"{len(results)}/{len(tasks)} matches in {time.monotonic() - start:.1f}s", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["smoke", "screen", "refine", "alternatives", "weaver", "tournament", "validate"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--extra", type=Path, nargs="*")
    parser.add_argument("--output", type=Path, default=Path(".context/stables-highway.json"))
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--finalists", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261020)
    args = parser.parse_args()
    if args.mode not in {"smoke", "screen"} and args.input is None:
        parser.error(f"{args.mode} requires --input")
    if args.workers < 1 or args.finalists < 1:
        parser.error("--workers and --finalists must be positive")
    if args.games <= 0 or args.games % 2:
        parser.error("--games must be positive and even for seat balance")
    if args.mode == "smoke":
        print(json.dumps(match((ENGINE, STABLES, 10, 100)), indent=2))
        return
    if args.mode == "screen":
        tasks = [(a, b, args.games, 10000 + 1000 * i + 50 * j)
                 for i, a in enumerate(candidates(args.seed)) for j, b in enumerate(PANEL)]
    elif args.mode in {"alternatives", "weaver"}:
        # Deliberately clean synergistic families, independent of the screen's
        # leading money plans: no unrelated support is required to try curses.
        specs = []
        for hut, weaver, inn, draw in itertools.product((1, 2), (0, 1, 2), (1, 2), (0, 2)):
            specs.append(dict(hut=hut, weaver=weaver, inn=inn, stables=draw,
                              silver=4, gold=99, green=0, opening="Weaver", order="attack"))
        for draw, attack in itertools.product((0, 1, 2, 4), (0, 1)):
            specs.append(dict(haggler=1, stables=draw, margrave=attack,
                              terminal_limit=2, silver=4, opening="auto"))
        for draw, fuel in itertools.product((0, 2), (4, 6, 99)):
            specs.append(dict(weaver=1, margrave=1, terminal_limit=2, stables=draw,
                              gain_silver=fuel, silver=5, opening="Weaver"))
        for draw, attack in itertools.product((0, 2), (0, 1)):
            specs.append(dict(develop=1, stables=draw, margrave=attack,
                              silver=4, opening="Develop"))
            specs.append(dict(dog=1, stables=draw, margrave=attack,
                              terminal_limit=2, silver=4, opening="Guard Dog"))
        if args.mode == "weaver":
            specs = [dict(weaver=weaver, margrave=1, terminal_limit=weaver + 1,
                          silver=fuel, gain_silver=gains, opening=opening)
                     for weaver, fuel, gains, opening in itertools.product(
                         (1, 2), (3, 5), (4, 6, 99), ("auto", "Weaver"))]
        leaders = [p for _, p in rank(json.loads(args.input.read_text()), screen=True)[:3]]
        panel = leaders + PANEL[1:]
        tasks = [(a, b, args.games, (5000000 if args.mode == "weaver" else 4000000) + 1000 * i + 50 * j)
                 for i, a in enumerate(specs) for j, b in enumerate(panel)]
    elif args.mode == "refine":
        previous = json.loads(args.input.read_text())
        ordered = rank(previous, screen=True)
        leaders = [p for _, p in ordered[:8]]
        for family in ("hut", "haggler", "weaver", "develop", "cartographer"):
            specialist = next((p for _, p in ordered if p.get(family, 0)), None)
            if specialist is not None and specialist not in leaders:
                leaders.append(specialist)
        panel = leaders[:4] + PANEL[1:]
        rng = random.Random(args.seed)
        specs = list(leaders)
        for attacks, fuel, duchy in itertools.product((1, 2, 3), (2, 3, 4, 5, 6, 99), (2, 3, 4, 5)):
            specs.append(dict(margrave=attacks, terminal_limit=attacks, silver=fuel,
                              duchy=duchy, opening="auto"))
        for draw, discount, village in itertools.product((0, 1, 2, 3, 4, 6), (0, 1, 2, 3), (0, 1)):
            specs.append(dict(stables=draw, highway=discount, inn=village,
                              margrave=1, silver=5, gold=99, green=0, opening="auto"))
        domains = dict(stables=[0, 1, 2, 3, 4, 5, 6, 8], highway=[0, 1, 2, 3, 4, 6, 8],
                       margrave=[0, 1, 2, 3], inn=[0, 1, 2, 3, 4], hut=[0, 1, 2],
                       haggler=[0, 1, 2], dog=[0, 1, 2], develop=[0, 1], weaver=[0, 1, 2],
                       cartographer=[0, 1, 2], silver=[2, 4, 6, 8, 99], gold=[0, 2, 4, 99],
                       green=[0, 6, 8, 10, 12, 14], duchy=[2, 3, 4, 5],
                       opening=["auto", "Silver", "Guard Dog", "Weaver", "Develop"],
                       order=["draw", "highway", "attack"], gain_silver=[2, 4, 6, 99],
                       terminal_limit=[1, 2, 3])
        # Joint edits retain interactions such as draw/fuel, village/terminal,
        # and discounts/greening. A second random seed supplies new neighbors.
        for _ in range(100):
            base = dict(rng.choice(leaders))
            for key in rng.sample(list(domains), rng.choice([1, 2, 3, 4])):
                base[key] = rng.choice(domains[key])
            specs.append(base)
        specs = list({json.dumps(p, sort_keys=True): p for p in specs}.values())
        tasks = [(a, b, args.games, 1000000 + 1000 * i + 50 * j)
                 for i, a in enumerate(specs) for j, b in enumerate(panel)]
    elif args.mode == "tournament":
        results = json.loads(args.input.read_text())
        ordered = rank(results, screen=True)
        selected = [p for _, p in ordered[:args.finalists]]
        for family in ("stables", "hut"):
            specialist = next((p for _, p in ordered if p.get(family, 0)), None)
            if specialist is not None and specialist not in selected:
                selected.append(specialist)
        engine = next((p for _, p in ordered if p.get("highway", 0) and p.get("stables", 0)), None)
        if engine is not None and engine not in selected:
            selected.append(engine)
        if args.extra:
            extra = rank([r for path in args.extra for r in json.loads(path.read_text())], screen=True)
            selected += [p for _, p in extra[:4] if p not in selected]
            for family in ("hut", "haggler", "weaver", "develop", "dog"):
                specialist = next((p for _, p in extra if p.get(family, 0)), None)
                if specialist is not None and specialist not in selected:
                    selected.append(specialist)
        # Preserve clean synergistic families even if the broad panel favored
        # a different family. Simple Stables plans remain in the final league.
        for p in PANEL:
            if p not in selected:
                selected.append(p)
        tasks = [(a, b, args.games, 2000000 + 1000 * i + 50 * j)
                 for i, a in enumerate(selected) for j, b in enumerate(selected) if i < j]
    else:
        config = json.loads(args.input.read_text())
        tasks = [(config["winner"], p, args.games, 9000000 + 10000 * i)
                 for i, p in enumerate(config["opponents"])]
    results = run(tasks, args.output, args.workers)
    if args.mode == "validate":
        for r in results:
            print(f"{r['rate']:.3f} {r['wins']}W/{r['ties']}T/{r['games']} turns={r['turns']:.1f} truncated={r['truncated']} vs {r['b']}")
    else:
        for score, params in rank(results, screen=args.mode in {"screen", "refine", "alternatives", "weaver"})[:20]:
            print(f"{score:.4f} {json.dumps(params, sort_keys=True)}")


if __name__ == "__main__":
    main()
