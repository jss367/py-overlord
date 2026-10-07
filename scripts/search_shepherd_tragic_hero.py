"""Reproducible search and seat-balanced comparisons for the random kingdom."""

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
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.shepherd_tragic_hero import ShepherdTragicHero


BOARD = load_board("boards/shepherd_tragic_hero.txt")
MONEY = dict(shepherd=0, hero=0, monastery=0, silver=99, gold=99, opening="Silver")
PANEL = [
    MONEY,
    dict(MONEY, hero=2, opening="Tragic Hero"),
    {},
    dict(
        shepherd=4,
        hero=1,
        monastery=1,
        cobbler=1,
        exorcist=1,
        crypt=1,
        extra_estates=6,
        green=10,
        priority="night",
    ),
]


def match(task, strategy_type=ShepherdTragicHero):
    a, b, games, seed = task
    wins = ties = truncated = 0
    turns = 0
    scores = [0, 0]
    decks = [Counter(), Counter()]
    points = []
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(strategy_type(**a)), GeneticAI(strategy_type(**b))]
        if i % 2:
            ais.reverse()
        s = GameState(players=[], supply={})
        s.log_callback = lambda *_: None
        s.initialize_game(
            ais,
            [get_card(n) for n in BOARD.kingdom_cards],
        )
        while not s.is_game_over() and s.turn_number < 160:
            s.play_turn()
        truncated += not s._normal_game_end_reached()
        players = s.players if i % 2 == 0 else list(reversed(s.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        wins += keys[0] > keys[1]
        ties += keys[0] == keys[1]
        points.append(1.0 if keys[0] > keys[1] else 0.5 if keys[0] == keys[1] else 0.0)
        turns += s.turn_number
        for j, player in enumerate(players):
            scores[j] += keys[j][0]
            decks[j].update(c.name for c in player.all_cards())
    paired = [(points[i] + points[i + 1]) / 2 for i in range(0, games, 2)]
    se = statistics.stdev(paired) / len(paired) ** 0.5 if len(paired) > 1 else 0
    rate = (wins + ties / 2) / games
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        wins=wins,
        ties=ties,
        rate=rate,
        interval95=[max(0, rate - 1.96 * se), min(1, rate + 1.96 * se)],
        paired_scores=paired,
        turns=turns / games,
        scores=[x / games for x in scores],
        truncated=truncated,
        decks=[{k: round(v / games, 3) for k, v in sorted(d.items())} for d in decks],
    )


def cobbler_combinations(parent=None):
    """Explore the gain engine together, without unrelated support-card costs."""
    baseline = dict(shepherd=1, hero=1, monastery=0, silver=99, estate=3)
    if parent is not None:
        baseline.update(parent)
    return [
        dict(
            baseline,
            cobbler=cobbler,
            hero=hero,
            cobbler_shepherds=target,
            cobbler_estates=estates,
            cobbler_adaptive=adaptive,
            priority=priority,
            opening="Tragic Hero" if hero == 2 else "Shepherd",
        )
        for cobbler, hero, target, estates, adaptive, priority in itertools.product(
            [1, 2], [1, 2], [2, 4, 6], [0, 5], [False, True], ["draw", "night"]
        )
    ]


def candidates(seed=20261007, *, legacy=False):
    specs = list(PANEL)
    for hero, shepherd, monastery in itertools.product([1, 2, 3], [0, 1, 2, 4], [0, 1]):
        specs.append(
            dict(
                hero=hero,
                shepherd=shepherd,
                monastery=monastery,
                silver=99,
                keep_estates=bool(shepherd),
            )
        )
    for cave, hound in itertools.product([1, 2, 3], [1, 2, 3]):
        specs.append(
            dict(
                shepherd=0,
                hero=1,
                cave=cave,
                hound=hound,
                cave_mode=1,
                keep_estates=False,
                priority="cave",
            )
        )
    rng = random.Random(seed)
    for _ in range(120):
        specs.append(
            dict(
                shepherd=rng.choice([0, 1, 2, 3, 4, 6]),
                hero=rng.choice([0, 1, 2, 3]),
                monastery=rng.choice([0, 1, 1, 1]),
                monastery_timing=rng.choice(["early", "spare"]),
                cave=rng.choice([0, 0, 1, 2]),
                hound=rng.choice([0, 0, 1, 2]),
                exorcist=rng.choice([0, 0, 1]),
                cobbler=rng.choice([0, 0, 1, 2]),
                crypt=rng.choice([0, 0, 1]),
                guardian=rng.choice([0, 0, 1]),
                herbalist=rng.choice([0, 0, 1]),
                silver=rng.choice([2, 3, 5, 99]),
                gold=rng.choice([3, 5, 99]),
                green=rng.choice([0, 8, 10]),
                duchy=rng.choice([2, 3, 4]),
                estate=rng.choice([1, 2, 3]),
                extra_estates=rng.choice([0, 0, 5, 8]),
                opening=rng.choice(
                    ["Shepherd", "Silver", "Exorcist", "Tragic Hero", "Monastery"]
                ),
                priority=rng.choice(["draw", "money", "night", "cave"]),
                keep_estates=rng.choice([True, False]),
                cave_mode=rng.choice([0, 1]),
                imps=rng.choice([1, 2, 3]),
                ghosts=rng.choice([0, 1]),
            )
        )
    if not legacy:
        specs.extend(cobbler_combinations())
    return specs


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


def policy_key(spec):
    """Collapse settings that cannot affect a policy with those cards absent."""
    p = ShepherdTragicHero(**spec).params
    if not p["monastery"]:
        p["monastery_timing"] = "early"
    if not p["exorcist"]:
        p["imps"], p["ghosts"] = 2, 0
    if not p["monastery"] and not p["exorcist"]:
        p["keep_estates"] = True
    if not p["cave"]:
        p["cave_mode"] = 0
    if not p["crypt"]:
        p["crypt_min"] = 2
    if not p["shepherd"]:
        p["extra_estates"] = 0
    if not p["cobbler"]:
        p["cobbler_shepherds"] = None
    if p["cobbler_shepherds"] is None:
        p["cobbler_estates"], p["cobbler_silver"], p["cobbler_adaptive"] = 0, 0, False
    return json.dumps(p, sort_keys=True)


def ranking(results):
    totals, counts, specs = Counter(), Counter(), {}
    for r in results:
        for side, score in [("a", r["rate"]), ("b", 1 - r["rate"])]:
            key = policy_key(r[side])
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
        key = policy_key(result["a"])
        totals[key] += result["rate"]
        counts[key] += 1
        specs[key] = result["a"]
    return [
        (totals[k] / counts[k], specs[k])
        for k in sorted(totals, key=lambda k: -totals[k] / counts[k])
    ]


def refinement_parents(ordered, *, legacy=False):
    """Retain a gain-engine candidate even when the first screen favors money."""
    parents = [p for _, p in ordered[:4]]
    if not legacy:
        engine = next(
            (
                p
                for _, p in ordered
                if p.get("cobbler_shepherds", 0) and p.get("cobbler", 0)
            ),
            None,
        )
        if engine is not None and policy_key(engine) not in {
            policy_key(p) for p in parents
        }:
            parents.append(engine)
    return parents


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=["smoke", "search", "refine", "tournament", "validation", "ablation"],
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--extra", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path(".context/shepherd-search.json")
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument(
        "--legacy-policy-space",
        action="store_true",
        help="Reproduce the original candidate generation and one-setting refinement.",
    )
    args = parser.parse_args()
    if args.mode == "smoke":
        print(json.dumps(match(({}, MONEY, 8, 100)), indent=2))
        return
    if args.mode == "search":
        games = 32 if args.legacy_policy_space else 96
        tasks = [
            (a, b, games, args.seed + 1000 * i + 100 * j)
            for i, a in enumerate(
                candidates(args.seed, legacy=args.legacy_policy_space)
            )
            for j, b in enumerate(PANEL)
        ]
    else:
        previous = json.loads(args.input.read_text())
        ordered = (
            ranking if args.mode in {"validation", "ablation"} else screening_ranking
        )(previous)
        if args.mode == "refine":
            parents = refinement_parents(ordered, legacy=args.legacy_policy_space)
            variants = list(parents)
            options = dict(
                shepherd=[0, 1, 2, 3, 4],
                hero=[0, 1, 2, 3, 4],
                monastery=[0, 1, 2],
                monastery_timing=["early", "spare"],
                crypt=[0, 1, 2],
                cobbler=[0, 1, 2],
                exorcist=[0, 1],
                cave=[0, 1],
                hound=[0, 1],
                guardian=[0, 1],
                herbalist=[0, 1],
                silver=[2, 4, 99],
                green=[0, 8, 10],
                duchy=[2, 4, 5],
                estate=[1, 2, 3],
                keep_estates=[True, False],
                extra_estates=[0, 5, 8],
                opening=["Shepherd", "Silver", "Monastery", "Tragic Hero"],
            )
            for p in parents:
                for key, vals in options.items():
                    variants += [dict(p, **{key: v}) for v in vals]
            if not args.legacy_policy_space:
                variants.extend(cobbler_combinations())
                for p in parents:
                    if p.get("cobbler", 0):
                        variants.extend(cobbler_combinations(p))
                        for key, values in {
                            "cobbler_silver": [0, 1, 2],
                            "cobbler_estates": [0, 4, 5, 6, 8],
                            "cobbler_shepherds": [1, 2, 3, 4, 6],
                            "cobbler_adaptive": [False, True],
                        }.items():
                            variants.extend(dict(p, **{key: v}) for v in values)
            unique = {
                json.dumps(ShepherdTragicHero(**p).params, sort_keys=True): p
                for p in variants
            }
            panel = parents[:3] + [PANEL[1]]
            games = 40 if args.legacy_policy_space else 80
            tasks = [
                (a, b, games, args.seed + 1000 * i + 100 * j)
                for i, a in enumerate(unique.values())
                for j, b in enumerate(panel)
            ]
        elif args.mode == "tournament":
            finalists = [p for _, p in ordered[:8]]
            if args.extra:
                extra = screening_ranking(json.loads(args.extra.read_text()))
                seen = {policy_key(p) for p in finalists}
                for _, p in extra[:4]:
                    if policy_key(p) not in seen:
                        finalists.append(p)
                        seen.add(policy_key(p))
            tasks = [
                (a, b, 400, args.seed + 1000 * i)
                for i, (a, b) in enumerate(itertools.combinations(finalists, 2))
            ]
        elif args.mode == "ablation":
            champion = ordered[0][1]
            baseline = ShepherdTragicHero(**champion).params
            opponents = []
            for key in (
                "shepherd",
                "hero",
                "monastery",
                "crypt",
                "cobbler",
                "exorcist",
                "guardian",
                "cave",
                "hound",
                "herbalist",
            ):
                opponents.append(dict(baseline, **{key: 0 if baseline[key] else 1}))
            opponents += [dict(baseline, keep_estates=not baseline["keep_estates"])]
            tasks = [
                (champion, b, 600, args.seed + 1000 * i)
                for i, b in enumerate(opponents)
            ]
        else:
            champion = ordered[0][1]
            opponents = [p for _, p in ordered[1:5]] + PANEL
            tasks = [
                (champion, b, 1000, args.seed + 1000 * i)
                for i, b in enumerate(opponents)
            ]
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
        print(json.dumps(ranking(results), indent=2))
    else:
        print(
            json.dumps(
                [
                    {k: r[k] for k in ("b", "games", "wins", "ties", "rate")}
                    for r in results
                ],
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
