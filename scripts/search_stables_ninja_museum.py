"""Reproduce the paired-seat search on the Stables / Ninja / Museum kingdom."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import functools
import inspect
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
    """Sample the policy space, including the deck's own economy.

    The first pass of this search pinned ``silvers``/``golds``/``platinums``/
    ``province_at``/``money`` at their defaults, so every policy it scored was
    locked to two Platinums, one Gold and two Silvers and greened on the first
    affordable Colony. That capped what any draw engine could ever pay for,
    and it hid a better money buy order. They are sampled here.
    """
    specs = [{}]
    for opening, second in itertools.product(("Ninja", "Silk Merchant", "Conclave"), ("Catapult", "Watchtower", "Silver")):
        specs.append(dict(opening=opening, second=second))
    rng = random.Random(17092026)
    for _ in range(230):
        specs.append(dict(opening=rng.choice(["Ninja", "Silk Merchant", "Conclave", "Watchtower", "Silver"]),
                          second=rng.choice(["Catapult", "Watchtower", "Silver", "Harbor Village"]),
                          stables=rng.choice([0, 1, 2, 3, 4, 5, 6]), silks=rng.choice([0, 1, 2, 3, 4, 6]),
                          villages=rng.choice([0, 1, 2, 3, 4]), ninjas=rng.choice([0, 1, 1, 2]),
                          catapults=rng.choice([0, 0, 1, 2]), watchtowers=rng.choice([0, 1, 1, 2]),
                          conclaves=rng.choice([0, 1, 2, 3, 4]), innkeepers=rng.choice([0, 0, 1, 2]),
                          figurines=rng.choice([0, 1, 2, 3, 4, 6]), pendants=rng.choice([0, 1, 2, 3, 5]),
                          silvers=rng.choice([0, 2, 3, 4, 6, 8]), golds=rng.choice([0, 1, 2, 3, 4, 6]),
                          platinums=rng.choice([0, 1, 2, 3, 4]), province_at=rng.choice([0, 2, 4, 6]),
                          money=rng.choice([True, False]),
                          green_turn=rng.choice([12, 14, 17, 20, 25]), credit=rng.choice([True, False]),
                          curse_silver=rng.choice([True, False]), keep_copper=rng.choice([1, 3, 5, 7]),
                          ninja_first=rng.choice([True, False])))
    return specs


BASELINES = [
    dict(money=True, opening="Silver", second="Silver", stables=0, silks=0, villages=0,
         ninjas=0, catapults=0, watchtowers=0, conclaves=0, figurines=0, pendants=0, silvers=8, golds=8),
    dict(money=True, opening="Ninja", second="Silver", stables=2, silks=0, villages=0,
         ninjas=1, catapults=0, watchtowers=0, conclaves=0, figurines=0, pendants=0, silvers=6, golds=8),
    dict(opening="Silk Merchant", second="Catapult", stables=0, silks=6, villages=4),
    dict(opening="Ninja", second="Watchtower", stables=0, silks=0, villages=0,
         catapults=0, conclaves=0, figurines=6, pendants=5, silvers=3, golds=2),
    # Hand-proposed seed, like the six-Figurine baseline above it. Buying Gold
    # ahead of the last Figurine was found by hand before the sweep could reach
    # it, because it needs two fields to move at once.
    dict(opening="Ninja", second="Watchtower", stables=0, silks=1, villages=0,
         catapults=0, conclaves=0, figurines=3, pendants=5, silvers=3, golds=2,
         money=True),
]

# The policy this search published on 2026-09-17, kept as a fixed yardstick so
# every later run reports how much it moved.
SUPERSEDED = dict(opening="Ninja", second="Watchtower", stables=0, silks=0, villages=0,
                  catapults=0, conclaves=0, figurines=3, pendants=5, silvers=3, golds=2)

# The Stables engine that the 2026-09-17 search called its strongest. That run
# reported SUPERSEDED beating it 72.3%, measured while the Action ordering
# played Watchtower ahead of Stables. The ``regression`` stage replays the same
# pairing so the corrected number stays checkable.
PREVIOUS_ENGINE = dict(catapults=1, conclaves=1, credit=False, curse_silver=False,
                       figurines=1, green_turn=25, innkeepers=0, keep_copper=1,
                       ninjas=1, opening="Conclave", pendants=0, second="Watchtower",
                       silks=2, stables=3, villages=3, watchtowers=2)


# Every field the policy class exposes, so nothing stays pinned by omission.
REFINE_SWEEP = {
    "opening": ["Ninja", "Silk Merchant", "Conclave", "Watchtower", "Silver"],
    "second": ["Watchtower", "Catapult", "Silver", "Harbor Village"],
    "figurines": [0, 1, 2, 3, 4, 5, 6, 8],
    "pendants": [0, 1, 2, 3, 5, 8],
    "stables": [0, 1, 2, 3, 4], "silks": [0, 1, 2, 3],
    "conclaves": [0, 1, 2], "villages": [0, 1, 2, 3],
    "ninjas": [0, 1, 2], "catapults": [0, 1], "watchtowers": [0, 1, 2],
    "innkeepers": [0, 1],
    "silvers": [0, 2, 3, 4, 6, 8], "golds": [0, 1, 2, 3, 4, 6],
    "platinums": [0, 1, 2, 3, 4], "province_at": [0, 2, 4, 6],
    "money": [False, True], "keep_copper": [1, 3, 5, 7],
    "curse_silver": [False, True],
    "credit": [False, True], "ninja_first": [False, True],
    "green_turn": [12, 17, 22, 27], "museum": [False, True],
}


def stalled_specs(results):
    """Specs that hit the turn cap in any game.

    Mutual Catapult trashing can leave both decks unable to buy anything, so a
    wide screen samples a few policies that never reach a normal ending. They
    are disqualified rather than tolerated: no truncated game may influence a
    published number, and a policy that can stall is not one to recommend.
    """
    return {spec_key(r["a"]) for r in results if r["totals"]["truncated"]}


def rank_policies(results, *, both_sides=False):
    """Rank by mean score, retaining encounter order for equal scores."""
    grouped = {}
    for result in results:
        sides = [(result["a"], result["rate"])]
        if both_sides:
            sides.append((result["b"], 1 - result["rate"]))
        for spec, rate in sides:
            grouped.setdefault(spec_key(spec), []).append(rate)
    return [json.loads(key) for key in sorted(
        grouped, key=lambda key: statistics.mean(grouped[key]), reverse=True
    )]


def validation_policies(refined, finalists):
    """The field that decides the published policy.

    An earlier version of this search froze ``refined[0]`` and only then
    measured it. A coordinate sweep at a few hundred games per variant ranks
    partly on noise, so the frozen policy was not reliably the best one in its
    own shortlist. The winner is now decided by the ``validate`` round robin
    over this field, and re-measured on fresh seeds by ``confirm``.
    """
    field = [*refined[:5], finalists[0], SUPERSEDED,
             BASELINES[0], BASELINES[1], BASELINES[2]]
    unique = {spec_key(spec): normalize(spec) for spec in field}
    return list(unique.values())


@functools.cache
def class_defaults():
    """The policy class's own defaults, so an ablation reverts to real values."""
    return {name: param.default
            for name, param in inspect.signature(StablesNinjaMuseum).parameters.items()
            if param.default is not inspect.Parameter.empty}


def normalize(spec):
    """Fill in class defaults so equivalent specs compare equal.

    Two specs that differ only in whether a field is spelled out are the same
    policy. Left unnormalized they survive deduplication as separate entrants,
    and the round robin then schedules the winner against itself and averages
    a guaranteed 50% into its own score.
    """
    return {**class_defaults(), **spec}


def spec_key(spec):
    return json.dumps(normalize(spec), sort_keys=True)


def is_engine(spec):
    """A policy that buys Stables or Harbor Village, using the class defaults."""
    return spec.get("stables", 4) > 0 or spec.get("villages", 2) > 0


def round_robin_ranking(results):
    """Average score rate per policy across every pairing it appeared in."""
    rates = {}
    for result in results:
        for spec, rate in ((result["a"], result["rate"]),
                           (result["b"], 1 - result["rate"])):
            rates.setdefault(spec_key(spec), []).append(rate)
    return sorted(((statistics.mean(v), json.loads(k)) for k, v in rates.items()),
                  key=lambda pair: -pair[0])


def run_matches(tasks, workers):
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(match, tasks):
            results.append(r)
            if len(results) % 10 == 0:
                print(f"{len(results)}/{len(tasks)} matchups", flush=True)
    return results


def report_truncation(results, stage, output):
    """Reject turn-capped games before they reach an evidence file.

    Only the screen tolerates stalls, and its stalled specs are then
    disqualified, so no published comparison contains a truncated game. A
    rejected run is parked next to its output rather than discarded, so the
    games are still there to inspect without looking like retained evidence.
    """
    truncated = sum(r["totals"]["truncated"] for r in results)
    if truncated and stage != "screen":
        write_json(output.with_suffix(".rejected.json"),
                   dict(stage=stage, rejected=True, results=results))
        raise RuntimeError(
            f"{truncated} truncated games require inspection; results parked at "
            f"{output.with_suffix('.rejected.json')}")
    if truncated:
        print(f"{truncated} screened games hit the turn cap; those policies are "
              f"disqualified at the next stage")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["screen", "final", "refine", "validate",
                                            "confirm", "engines", "ablate", "regression",
                                            "rank-final", "rank-refine"],
                        default="screen")
    parser.add_argument("--games", type=int, default=80)
    parser.add_argument("--seed", type=int, default=170000)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=3,
                        help="Coordinate-ascent rounds for the refine stage.")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--final-ranked", type=Path,
                        help="Finalist ranking to use when selecting validation opponents")
    parser.add_argument("--policies-output", type=Path,
                        help="Write validation policies during rank-refine")
    args = parser.parse_args()
    if args.stage == "engines" and args.final_ranked is None:
        parser.error("engines requires --final-ranked")
    if args.stage != "screen" and args.stage != "regression" and args.input is None:
        parser.error("--input is required outside the screen stage")
    if args.output is None:
        suffix = {"rank-final": "final_ranked", "rank-refine": "refine_ranked",
                  "validate": "validation",
                  "confirm": "confirmation",
                  "engines": "engines",
                  "ablate": "ablation",
                  "regression": "regression"}.get(args.stage, args.stage)
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
        # Iterated coordinate ascent. One sweep from a single base can only
        # reach policies that differ from it in one field, so the previous
        # version of this search could never combine two separate improvements.
        # Every round scores against the same two opponents, which keeps rates
        # comparable across rounds for the ranking stage.
        ranked = json.loads(args.input.read_text())
        opponents = ranked[:2]
        base, seen, results = ranked[0], set(), []
        for rnd in range(args.rounds):
            variants = {spec_key(base): base}
            for key, values in REFINE_SWEEP.items():
                for value in values:
                    cand = dict(base, **{key: value})
                    variants.setdefault(spec_key(cand), cand)
            fresh = [v for k, v in variants.items() if k not in seen]
            seen.update(variants)
            tasks = [(spec, opponent, args.games, args.seed + j*10000)
                     for spec in fresh for j, opponent in enumerate(opponents)]
            print(f"refine round {rnd}: {len(fresh)} new variants, "
                  f"{len(tasks)} matchups", flush=True)
            if not tasks:
                break
            results += run_matches(tasks, args.workers)
            ranking = rank_policies(results)
            if ranking[0] == base:
                print(f"refine converged after round {rnd}", flush=True)
                break
            base = ranking[0]
        report_truncation(results, args.stage, args.output)
        write_json(args.output, dict(stage="refine", results=results))
        print(f"Saved {len(results)} matchups / {sum(r['games'] for r in results)} "
              f"games to {args.output}")
        return
    elif args.stage == "final":
        data = json.loads(args.input.read_text())["results"]
        stalled = stalled_specs(data)
        ranked = [s for s in rank_policies(data) if spec_key(s) not in stalled]
        if stalled:
            print(f"Disqualified {len(stalled)} screened policies that hit the turn cap")
        specs = ranked[:8] + BASELINES
        tasks = [(a,b,args.games,args.seed) for a,b in itertools.combinations(specs,2)]
    elif args.stage == "validate":
        specs = json.loads(args.input.read_text())
        tasks = [(a, b, args.games, args.seed)
                 for a, b in itertools.combinations(specs, 2)]
    elif args.stage == "regression":
        tasks = [(SUPERSEDED, PREVIOUS_ENGINE, args.games, args.seed)]
    elif args.stage == "ablate":
        # One field at a time: a multi-field "variant" cannot attribute its
        # result to any single setting.
        data = json.loads(args.input.read_text())
        if data["stage"] != "validate":
            parser.error("ablate requires results from validate")
        winner = round_robin_ranking(data["results"])[0][1]
        defaults = class_defaults()
        tasks = [(winner, dict(winner, **{key: defaults[key]}), args.games, args.seed)
                 for key in sorted(winner) if winner[key] != defaults.get(key)]
        print(f"Reverting {len(tasks)} fields of the winner one at a time")
    elif args.stage == "engines":
        data = json.loads(args.input.read_text())
        if data["stage"] != "validate":
            parser.error("engines requires results from validate")
        winner = round_robin_ranking(data["results"])[0][1]
        finalists = json.loads(args.final_ranked.read_text())
        engines = [spec for spec in finalists if is_engine(spec)][:3]
        print(f"Winner vs the {len(engines)} strongest engine finalists")
        tasks = [(winner, spec, args.games, args.seed) for spec in engines]
    else:
        data = json.loads(args.input.read_text())
        if data["stage"] != "validate":
            parser.error("confirm requires results from validate")
        ranking = round_robin_ranking(data["results"])
        winner = ranking[0][1]
        print(f"Round-robin winner {ranking[0][0]*100:.1f}%: "
              f"{json.dumps(winner, sort_keys=True)}")
        tasks = [(winner, spec, args.games, args.seed)
                 for _, spec in ranking[1:]]
    results = run_matches(tasks, args.workers)
    report_truncation(results, args.stage, args.output)
    write_json(args.output, dict(stage=args.stage, results=results))
    print(f"Saved {len(results)} matchups / {sum(r['games'] for r in results)} games to {args.output}")


if __name__ == "__main__":
    main()
