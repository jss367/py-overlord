"""Reproduce the paired-seat search on the Stables / Ninja / Museum kingdom."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import random
import statistics

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.landmarks.registry import get_landmark
from dominion.strategy.strategies.stables_ninja_museum import KINGDOM, StablesNinjaMuseum


def match(task):
    a, b, games, seed = task
    outcomes, totals = [], Counter()
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(StablesNinjaMuseum(**a)), GeneticAI(StablesNinjaMuseum(**b))]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(ais, [get_card(n) for n in (*KINGDOM, "Platinum", "Colony")],
                              events=[get_event("Credit")], landmarks=[get_landmark("Museum")])
        assert state.supply["Colony"] == 8 and state.supply["Catapult"] == 5
        while not state.is_game_over() and state.turn_number < 180:
            state.play_turn()
        player, opponent = state.players[i % 2], state.players[1 - i % 2]
        key = lambda p: (p.get_victory_points(), -p.turns_taken)
        score = 1. if key(player) > key(opponent) else .5 if key(player) == key(opponent) else 0.
        outcomes.append(score)
        totals["wins"] += score == 1
        totals["ties"] += score == .5
        totals["truncated"] += not state._normal_game_end_reached()
        totals["turns"] += state.turn_number
        totals["score"] += player.get_victory_points()
        totals["opponent_score"] += opponent.get_victory_points()
        totals["museum_points"] += 2 * len({c.name for c in player.all_cards()})
    rate = statistics.mean(outcomes)
    pairs = [statistics.mean(outcomes[i:i+2]) for i in range(0, games, 2)]
    se = statistics.stdev(pairs) / len(pairs)**.5 if len(pairs) > 1 else 0
    interval = [max(0, rate-1.96*se), min(1, rate+1.96*se)]
    # At a boundary the normal interval degenerates; use a Wilson bound
    # with the number of independent seed pairs as the effective sample size.
    if rate in (0, 1):
        margin = 1.96**2 / (len(pairs) + 1.96**2)
        interval = [0, margin] if rate == 0 else [1-margin, 1]
    return dict(a=a, b=b, games=games, seed=seed, rate=rate,
                paired_ci95=interval, totals=dict(totals))


def candidates():
    specs = [{}]
    for opening, second in itertools.product(("Ninja", "Silk Merchant", "Conclave"), ("Catapult", "Watchtower", "Silver")):
        specs.append(dict(opening=opening, second=second))
    rng = random.Random(17092026)
    for _ in range(62):
        specs.append(dict(opening=rng.choice(["Ninja", "Silk Merchant", "Conclave"]),
                          second=rng.choice(["Catapult", "Watchtower", "Silver"]),
                          stables=rng.choice([0, 2, 3, 4, 5, 6]), silks=rng.choice([0, 1, 2, 4, 6]),
                          villages=rng.choice([1, 2, 3]), ninjas=rng.choice([0, 1, 1, 2]),
                          catapults=rng.choice([0, 1, 1, 2]), watchtowers=rng.choice([0, 1, 2]),
                          conclaves=rng.choice([0, 1, 2, 4]), innkeepers=rng.choice([0, 0, 1]),
                          figurines=rng.choice([0, 1, 3]), pendants=rng.choice([0, 1, 3, 5]),
                          green_turn=rng.choice([14, 17, 20, 25]), credit=rng.choice([True, False]),
                          curse_silver=rng.choice([True, False]), keep_copper=rng.choice([1, 3, 5])))
    return specs


BASELINES = [
    dict(money=True, opening="Silver", second="Silver", stables=0, silks=0, villages=0,
         ninjas=0, catapults=0, watchtowers=0, conclaves=0, figurines=0, pendants=0, silvers=8, golds=8),
    dict(money=True, opening="Ninja", second="Silver", stables=2, silks=0, villages=0,
         ninjas=1, catapults=0, watchtowers=0, conclaves=0, figurines=0, pendants=0, silvers=6, golds=8),
    dict(opening="Silk Merchant", second="Catapult", stables=0, silks=6, villages=4),
    dict(opening="Ninja", second="Watchtower", stables=0, silks=0, villages=0,
         catapults=0, conclaves=0, figurines=6, pendants=5, silvers=3, golds=2),
]


def rank_policies(results, *, both_sides=False):
    """Rank by mean score, retaining encounter order for equal scores."""
    grouped = {}
    for result in results:
        sides = [(result["a"], result["rate"])]
        if both_sides:
            sides.append((result["b"], 1 - result["rate"]))
        for spec, rate in sides:
            key = json.dumps(spec, sort_keys=True)
            grouped.setdefault(key, []).append(rate)
    return [json.loads(key) for key in sorted(
        grouped, key=lambda key: statistics.mean(grouped[key]), reverse=True
    )]


def validation_policies(refined, finalists):
    """Freeze the winner, close challengers, original finalists and baselines."""
    best = refined[0]
    return [best, refined[1], finalists[0], finalists[1],
            BASELINES[0], BASELINES[1], BASELINES[2],
            dict(best, silks=1), dict(best, second="Silver")]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["screen", "final", "refine", "validate", "rank-final", "rank-refine"], default="screen")
    parser.add_argument("--games", type=int, default=80)
    parser.add_argument("--seed", type=int, default=170000)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--final-ranked", type=Path,
                        help="Finalist ranking to use when selecting validation opponents")
    parser.add_argument("--policies-output", type=Path,
                        help="Write validation policies during rank-refine")
    args = parser.parse_args()
    if args.stage != "screen" and args.input is None:
        parser.error("--input is required outside the screen stage")
    if args.output is None:
        suffix = {"rank-final": "final_ranked", "rank-refine": "refine_ranked",
                  "validate": "validation"}.get(args.stage, args.stage)
        args.output = Path(f"scripts/data/stables_ninja_museum_{suffix}.json")
    if args.stage.startswith("rank-"):
        if args.stage == "rank-refine" and (args.final_ranked is None or args.policies_output is None):
            parser.error("rank-refine requires --final-ranked and --policies-output")
        data = json.loads(args.input.read_text())
        expected_stage = "final" if args.stage == "rank-final" else "refine"
        if data["stage"] != expected_stage:
            parser.error(f"{args.stage} requires results from {expected_stage}")
        ranked = rank_policies(data["results"], both_sides=args.stage == "rank-final")
        write_json(args.output, ranked)
        if args.stage == "rank-refine":
            finalists = json.loads(args.final_ranked.read_text())
            write_json(args.policies_output, validation_policies(ranked, finalists))
        print(f"Ranked {len(ranked)} policies into {args.output}")
        return
    if args.games < 4 or args.games % 2:
        parser.error("--games must be an even number >= 4")
    if args.stage == "screen":
        tasks = [(s, b, args.games, args.seed + j*10000) for s in candidates() for j,b in enumerate([{}, BASELINES[1]])]
    elif args.stage == "refine":
        ranked = json.loads(args.input.read_text())
        best = ranked[0]
        variants = [best]
        for key, values in {
            "opening": ["Ninja", "Silk Merchant", "Conclave", "Figurine"],
            "second": ["Watchtower", "Catapult", "Silver"],
            "figurines": [2, 3, 4, 5, 6, 8, 10],
            "pendants": [0, 1, 2, 3, 5, 8],
            "stables": [0, 1, 2, 3],
            "silks": [0, 1, 2], "conclaves": [0, 1, 2],
            "villages": [0, 1, 2], "ninjas": [0, 1, 2],
            "catapults": [0, 1], "watchtowers": [0, 1],
            "credit": [False, True], "ninja_first": [False, True],
            "green_turn": [12, 17, 22, 27], "museum": [False, True],
        }.items():
            variants += [dict(best, **{key: v}) for v in values]
        unique = {json.dumps(v, sort_keys=True): v for v in variants}
        tasks = [(s, b, args.games, args.seed + j*10000)
                 for s in unique.values() for j,b in enumerate(ranked[:2])]
    elif args.stage == "final":
        data = json.loads(args.input.read_text())["results"]
        specs = rank_policies(data)[:8] + BASELINES
        tasks = [(a,b,args.games,args.seed) for a,b in itertools.combinations(specs,2)]
    else:
        specs = json.loads(args.input.read_text())
        tasks = [(specs[0], b, args.games, args.seed) for b in specs[1:]]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(match, tasks):
            results.append(r)
            if len(results) % 10 == 0:
                print(f"{len(results)}/{len(tasks)} matchups", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(stage=args.stage, results=results), indent=2)+"\n")
    if any(r["totals"]["truncated"] for r in results):
        raise RuntimeError("Truncated games require inspection")
    print(f"Saved {len(results)} matchups / {sum(r['games'] for r in results)} games to {args.output}")


if __name__ == "__main__":
    main()
