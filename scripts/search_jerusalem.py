"""Seeded, seat-balanced search on the fixed Jerusalem board.

Kingdom: Goons, Sea Hag, Governor, Ambassador, Minion, Old Witch,
Scrying Pool, Fortress, Ill-Gotten Gains, Bridge Troll.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import itertools
import multiprocessing
import json
from pathlib import Path
import random
import time

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.jerusalem_seeds import DEFAULTS, Jerusalem
from dominion.strategy.strategy_loader import StrategyLoader


BOARD_PATH = "boards/jerusalem.txt"

#: Archetype panel. Every candidate is scored against all four. Each plan
#: lists every pile it wants; ``DEFAULTS`` contributes no kingdom cards.
MONEY = DEFAULTS | dict(
    old_witch=1, silver=99, gold=99, green=0, duchy=4, estate=2,
    opening="Silver", first_five="Old Witch", build="money")
#: Double cursing plus Goons -- the strongest money plan.
CURSE_GOONS = DEFAULTS | dict(
    sea_hag=1, old_witch=1, goons=2, silver=99, gold=99,
    green=0, duchy=4, estate=2, opening="Sea Hag", first_five="Old Witch",
    build="money")
#: Governor draw with Fortress villages -- the engine that looks obvious.
GOONS = DEFAULTS | dict(
    goons=3, governor=3, fortress=4, old_witch=1, ambassador=1,
    bridge_troll=1, silver=2, gold=2, green=12, duchy=5, estate=3,
    copper_floor=5, opening="Ambassador", first_five="Governor", build="goons")
#: Scrying Pool draw, Fortress villages, Ambassador thinning, Goons payload.
POOL = DEFAULTS | dict(
    scrying_pool=6, potion=2, fortress=5, goons=3, ambassador=1,
    bridge_troll=1, silver=3, gold=2, green=99, duchy=3, estate=1,
    copper_floor=5, opening="Potion", first_five="Scrying Pool", build="pool")
RUSH = DEFAULTS | dict(
    igg=10, sea_hag=1, silver=99, gold=0, green=0, duchy=8, estate=8,
    green_first=False, opening="Silver", first_five="Ill-Gotten Gains",
    build="rush")
PANEL = [MONEY, CURSE_GOONS, POOL, RUSH]


def make_strategy(spec):
    if "registered" in spec:
        strategy = StrategyLoader().get_strategy(spec["registered"])
        if strategy is None:
            raise ValueError(spec)
        return strategy
    return Jerusalem(**spec)


def match(task):
    a, b, games, seed = task
    board = load_board(BOARD_PATH)
    kingdom = [get_card(n) for n in board.kingdom_cards]
    wins = ties = truncated = 0
    turns = 0
    points = [0, 0]
    decks = [Counter(), Counter()]
    endings = Counter()
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(make_strategy(a)), GeneticAI(make_strategy(b))]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(ais, kingdom)
        while not state.is_game_over() and state.turn_number < 120:
            state.play_turn()
        truncated += not state._normal_game_end_reached()
        players = state.players if i % 2 == 0 else list(reversed(state.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        wins += keys[0] > keys[1]
        ties += keys[0] == keys[1]
        turns += sum(p.turns_taken for p in players) / 2
        endings["Province" if state.supply["Province"] == 0
                else "three piles" if state._normal_game_end_reached()
                else "turn limit"] += 1
        for j, p in enumerate(players):
            points[j] += keys[j][0]
            decks[j].update(c.name for c in p.all_cards())
    return dict(a=a, b=b, games=games, seed=seed, wins=wins, ties=ties,
                rate=(wins + ties / 2) / games, mean_turns_per_player=turns / games,
                points=[x / games for x in points], truncated=truncated,
                endings=dict(endings),
                decks=[{k: round(v / games, 3) for k, v in sorted(d.items())} for d in decks])


def unique(specs):
    return list({json.dumps(s, sort_keys=True): s for s in specs}.values())


def candidates():
    specs = list(PANEL)
    for build, opening, first_five in itertools.product(
        ("goons", "pool", "minion", "rush", "money"),
        ("Ambassador", "Silver", "Potion", "Fortress"),
        ("Scrying Pool", "Governor", "Old Witch", "Minion", "Ill-Gotten Gains"),
    ):
        base = {"goons": GOONS, "pool": POOL, "rush": RUSH,
                "money": CURSE_GOONS}.get(
            build, DEFAULTS | dict(minion=6, fortress=3, silver=99, gold=99,
                                   green=0, duchy=4, estate=2, build="minion"))
        specs.append(base | dict(build=build, opening=opening, first_five=first_five))
    rng = random.Random(20260917)
    for _ in range(96):
        pool = rng.choice([0, 0, 2, 4, 6, 8])
        specs.append(DEFAULTS | dict(
            goons=rng.choice([0, 1, 2, 3, 4]), sea_hag=rng.choice([0, 0, 1, 2]),
            governor=rng.choice([0, 1, 2, 3, 5]), ambassador=rng.choice([0, 1, 1, 2]),
            minion=rng.choice([0, 0, 2, 4, 6]), old_witch=rng.choice([0, 1, 1, 2]),
            scrying_pool=pool, potion=rng.choice([1, 2, 2, 3]) if pool else 0,
            fortress=rng.choice([0, 2, 3, 5, 7]), igg=rng.choice([0, 0, 3, 10]),
            bridge_troll=rng.choice([0, 0, 1, 2, 3]),
            silver=rng.choice([1, 2, 3, 99]), gold=rng.choice([0, 1, 2, 4, 99]),
            green=rng.choice([0, 8, 12, 14, 18, 99]), duchy=rng.choice([3, 4, 5, 8]),
            estate=rng.choice([1, 2, 3, 8]), green_first=rng.choice([True, False]),
            opening=rng.choice(["Ambassador", "Silver", "Potion", "Fortress", "Sea Hag"]),
            first_five=rng.choice(["Scrying Pool", "Governor", "Old Witch",
                                   "Minion", "Ill-Gotten Gains", "Silver"]),
            build=rng.choice(["goons", "pool", "minion", "rush", "money"]),
            governor_mode=rng.choice(["auto", "cards", "gold", "upgrade"]),
            minion_mode=rng.choice(["auto", "coins", "discard"]),
            pool_self=rng.choice(["actions", "junk"]),
            ambassador_max=rng.choice([1, 2]), ambassador_curse=rng.choice([True, False]),
            goons_filler=rng.choice([True, True, False]),
            filler=rng.choice(["Copper", "Estate", "Curse"]),
            copper_floor=rng.choice([0, 3, 4, 5, 7]),
        ))
    return unique(specs)


def ranking(results, both=False):
    scores, games, specs = Counter(), Counter(), {}
    for r in results:
        for side, score in [("a", r["wins"] + r["ties"] / 2)] + (
                [("b", r["games"] - r["wins"] - r["ties"] / 2)] if both else []):
            key = json.dumps(r[side], sort_keys=True)
            specs[key] = r[side]
            scores[key] += score
            games[key] += r["games"]
    return [dict(rate=scores[k] / games[k], games=games[k], spec=specs[k])
            for k in sorted(scores, key=lambda k: (-scores[k] / games[k], k))]


def refinement(leaders):
    specs = list(leaders)
    axes = dict(
        goons=[0, 1, 2, 3, 5], governor=[0, 1, 2, 3], fortress=[0, 2, 3, 5, 7],
        minion=[0, 2, 4, 6], scrying_pool=[0, 2, 4, 6, 8], igg=[0, 3, 10],
        old_witch=[0, 1, 2], sea_hag=[0, 1, 2], ambassador=[0, 1, 2, 3],
        bridge_troll=[0, 1, 2, 3], silver=[1, 2, 3, 99], gold=[0, 1, 2, 99],
        potion=[1, 2, 3], green=[0, 8, 12, 14, 18, 99], duchy=[3, 4, 5, 8],
        estate=[1, 2, 3, 8],
        opening=["Ambassador", "Silver", "Potion", "Fortress"],
        first_five=["Scrying Pool", "Governor", "Old Witch", "Minion",
                    "Ill-Gotten Gains"],
        governor_mode=["auto", "cards", "gold", "upgrade"],
        minion_mode=["auto", "coins", "discard"],
        goons_filler=[True, False], filler=["Copper", "Estate", "Curse"],
        green_first=[True, False], ambassador_max=[1, 2],
        copper_floor=[0, 3, 4, 5, 7], pool_self=["actions", "junk"],
        ambassador_curse=[True, False],
    )
    for base in leaders[:3]:
        for key, values in axes.items():
            specs.extend(base | {key: value} for value in values)
    return unique(specs)


def improving_moves(leader, refinement_record):
    """Single-field changes that beat the leader in a recorded refine run.

    ``refine`` sweeps one axis at a time, so its ranking says which single
    change helps but never whether two of them help together. This reads the
    winners off that record; ``combinations`` then tries them in company.
    """
    rates = {}
    for row in refinement_record["ranking"]:
        rates[json.dumps(row["spec"], sort_keys=True)] = row["rate"]
    baseline = rates.get(json.dumps(leader, sort_keys=True))
    best = {}
    for row in refinement_record["ranking"]:
        spec = row["spec"]
        changed = [k for k in spec if leader[k] != spec[k]]
        if len(changed) != 1:
            continue
        key = changed[0]
        if baseline is not None and row["rate"] <= baseline:
            continue
        if key not in best or row["rate"] > best[key][1]:
            best[key] = (spec[key], row["rate"])
    return {key: value for key, (value, _) in sorted(
        best.items(), key=lambda item: -item[1][1])}


def combinations_to_try(leader, moves, *, subsets=18, seed=4242):
    """Cumulative prefixes, leave-one-outs, and random subsets of ``moves``."""
    keys = list(moves)
    chosen = [frozenset()]
    chosen += [frozenset(keys[:i]) for i in range(1, len(keys) + 1)]
    chosen += [frozenset(keys) - {key} for key in keys]
    rng = random.Random(seed)
    for _ in range(subsets):
        size = rng.randint(2, max(2, len(keys) - 1))
        chosen.append(frozenset(rng.sample(keys, min(size, len(keys)))))
    return unique([
        leader | {key: moves[key] for key in subset}
        for subset in dict.fromkeys(chosen)
    ])


def ablations(winner):
    """One-field changes from the winner, so each row isolates one card."""
    rows = []
    for key in ("goons", "governor", "fortress", "minion", "scrying_pool",
                "igg", "old_witch", "sea_hag", "ambassador", "bridge_troll"):
        if winner.get(key):
            rows.append(winner | {key: 0})
    if winner.get("goons"):
        rows.append(winner | {"goons_filler": False})
    if winner.get("scrying_pool"):
        rows.append(winner | {"potion": 0, "scrying_pool": 0})
    return unique(rows)


def run(tasks, path, workers, mode):
    start = time.monotonic()
    results = []
    ctx = multiprocessing.get_context("fork")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        for result in pool.map(match, tasks):
            results.append(result)
            if len(results) % 25 == 0:
                print(f"{len(results)}/{len(tasks)} matches, "
                      f"{time.monotonic() - start:.1f}s", flush=True)
    output = dict(mode=mode, board=BOARD_PATH,
                  games=sum(r["games"] for r in results),
                  truncated=sum(r["truncated"] for r in results),
                  elapsed_seconds=time.monotonic() - start, results=results,
                  ranking=ranking(results, both=mode == "tournament"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n")
    for row in output["ranking"][:8]:
        print(f"{row['rate']:.3f} {json.dumps(row['spec'], sort_keys=True)}", flush=True)
    print(f"Saved {output['games']} games; {output['truncated']} truncated: {path}",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=["smoke", "search", "refine", "combine", "tournament",
                 "validate", "ablate"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--refine-input", type=Path,
                        help="refine record, required by the combine mode")
    parser.add_argument("--output", type=Path,
                        default=Path(".context/jerusalem-search.json"))
    parser.add_argument("--games", type=int, default=24)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--finalists", type=int, default=10)
    parser.add_argument(
        "--include", action="append", default=[], metavar="STRATEGY",
        help="add a registered strategy to a tournament field (repeatable)")
    args = parser.parse_args()
    if args.games < 2 or args.games % 2:
        parser.error("--games must be a positive even count for seat balance")
    if args.mode == "smoke":
        print(json.dumps(match((GOONS, MONEY, 8, 100)), indent=2))
        return
    if args.mode == "search":
        tasks = [(a, b, args.games, 100000 + j * 10000)
                 for a in candidates() for j, b in enumerate(PANEL)]
    else:
        if args.input is None:
            parser.error("this mode requires --input")
        previous = json.loads(args.input.read_text())
        leaders = [r["spec"] for r in previous["ranking"][:args.finalists]]
        if args.mode == "combine":
            if args.refine_input is None:
                parser.error("combine requires --refine-input")
            moves = improving_moves(
                leaders[0], json.loads(args.refine_input.read_text()))
            print(f"improving moves: {json.dumps(moves, sort_keys=True)}", flush=True)
            tasks = [(a, b, args.games, 950000 + i * 7000 + j * 100)
                     for i, a in enumerate(combinations_to_try(leaders[0], moves))
                     for j, b in enumerate(PANEL)]
        elif args.mode == "refine":
            opponents = unique(leaders[:3] + [POOL, CURSE_GOONS, MONEY])
            tasks = [(a, b, args.games, 300000 + j * 10000)
                     for a in refinement(leaders) for j, b in enumerate(opponents)]
        elif args.mode == "tournament":
            finalists = unique(
                leaders + PANEL + [{"registered": name} for name in args.include])
            tasks = [(a, b, args.games, 500000 + i * 10000)
                     for i, (a, b) in enumerate(itertools.combinations(finalists, 2))]
        elif args.mode == "ablate":
            winner = leaders[0]
            tasks = [(winner, b, args.games, 700000 + i * 10000)
                     for i, b in enumerate(ablations(winner))]
        else:
            winner = leaders[0]
            opponents = unique(leaders[1:5] + PANEL + [
                {"registered": "Big Money"},
                {"registered": "Big Money Smithy"},
            ])
            tasks = [(winner, b, args.games, 3000000 + i * 10000)
                     for i, b in enumerate(opponents)]
    run(tasks, args.output, args.workers, args.mode)


if __name__ == "__main__":
    main()
