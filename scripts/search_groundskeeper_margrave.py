"""Reproducible policy search for the ten-unused-card Groundskeeper board.

Modes
-----
``smoke``       one match, to check the harness runs.
``search``      broad screen of every candidate against a fixed panel.
``tournament``  seat-balanced round robin among the screen's finalists.

Every match alternates seats and re-seeds per game pair, so a result is
reproducible from its ``seed`` alone.
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
from dominion.strategy.strategies.groundskeeper_margrave import GroundskeeperMargrave


BOARD = load_board("boards/groundskeeper_margrave.txt")

# The panel is the yardstick every candidate is measured against: plain money,
# money plus the board's two cheapest payload upgrades, and one full engine.
MONEY = dict(silvers=3, golds=99, green=10, opening="Silver")
MONUMENT_MONEY = dict(MONEY, monument=1, moneylender=1, opening="Moneylender")
MARGRAVE_MONEY = dict(MONEY, margrave=1, opening="Silver")
ENGINE = dict(
    groundskeeper=2,
    margrave=2,
    junk_dealer=2,
    fishing_village=4,
    border_village=2,
    silvers=2,
    golds=3,
    green=12,
    duchy=4,
    estate_vp=True,
    opening="Silver",
)
PANEL = [MONEY, MONUMENT_MONEY, MARGRAVE_MONEY, ENGINE]

# Winner of the twelve-entrant finalist round robin, frozen before validation.
WINNER = dict(
    groundskeeper=0,
    margrave=1,
    library=2,
    monument=2,
    moneylender=0,
    junk_dealer=2,
    fishing_village=4,
    border_village=2,
    oasis=0,
    cellar=0,
    silvers=99,
    golds=3,
    green=12,
    duchy=4,
    estate_vp=True,
    opening="Silver",
)

# Runners-up from the same round robin, used as validation opponents.
RUNNER_UP = dict(
    MONEY,
    margrave=2,
    library=1,
    monument=2,
    moneylender=1,
    fishing_village=4,
    golds=4,
    duchy=4,
    opening="Fishing Village",
)
THIRD = dict(
    margrave=3,
    library=0,
    monument=2,
    moneylender=1,
    junk_dealer=1,
    fishing_village=5,
    border_village=1,
    oasis=2,
    silvers=3,
    golds=3,
    green=8,
    duchy=4,
    estate_vp=True,
    opening="Fishing Village",
)
NO_MONUMENT = dict(
    margrave=2,
    library=2,
    junk_dealer=2,
    fishing_village=5,
    silvers=3,
    golds=4,
    green=12,
    duchy=5,
    opening="Fishing Village",
)

TURN_LIMIT = 160


def match(task):
    """Play ``games`` seat-alternating games between two parameter dicts."""
    a, b, games, seed = task
    wins = ties = truncated = 0
    turns = 0
    scores = [0, 0]
    decks = [Counter(), Counter()]
    kingdom = [get_card(name) for name in BOARD.kingdom_cards]
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [
            GeneticAI(GroundskeeperMargrave(**a)),
            GeneticAI(GroundskeeperMargrave(**b)),
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
        truncated=truncated,
        decks=[
            {k: round(v / games, 2) for k, v in sorted(d.items())} for d in decks
        ],
    )


def candidates():
    """Named theories first, then a seeded random sweep around them."""
    named = list(PANEL)

    # How much Monument does a money deck want?
    for monument in (1, 2, 3):
        named.append(dict(MONEY, monument=monument, moneylender=1, opening="Moneylender"))

    # Margrave draw on a money chassis, with and without a village.
    for margrave, village in itertools.product((1, 2), (0, 2)):
        named.append(dict(MONEY, margrave=margrave, fishing_village=village))

    # Library variants: Library needs villages more than Margrave does.
    for library, village in itertools.product((1, 2), (0, 2, 4)):
        named.append(dict(MONEY, library=library, fishing_village=village, golds=4))

    # Groundskeeper engines at several greening speeds.
    for groundskeeper, green in itertools.product((1, 2, 3), (8, 10, 12)):
        named.append(
            dict(
                ENGINE,
                groundskeeper=groundskeeper,
                green=green,
                estate_vp=True,
            )
        )

    # Groundskeeper without the Estate-buying plan, to isolate that knob.
    for groundskeeper in (2, 3):
        named.append(dict(ENGINE, groundskeeper=groundskeeper, estate_vp=False))

    rng = random.Random(20260916)
    for _ in range(140):
        named.append(
            dict(
                groundskeeper=rng.choice([0, 0, 1, 2, 3]),
                margrave=rng.choice([0, 1, 1, 2, 3]),
                library=rng.choice([0, 0, 1, 2]),
                monument=rng.choice([0, 0, 1, 2]),
                moneylender=rng.choice([0, 0, 1]),
                junk_dealer=rng.choice([0, 1, 2]),
                fishing_village=rng.choice([0, 2, 3, 4, 5]),
                border_village=rng.choice([0, 0, 1, 2]),
                oasis=rng.choice([0, 0, 1, 2]),
                cellar=rng.choice([0, 0, 1]),
                silvers=rng.choice([1, 2, 3, 99]),
                golds=rng.choice([2, 3, 4, 99]),
                green=rng.choice([6, 8, 10, 12, 14]),
                duchy=rng.choice([3, 4, 5]),
                estate_vp=rng.choice([False, True]),
                opening=rng.choice(["Silver", "Moneylender", "Fishing Village"]),
            )
        )
    return named


def run(tasks, path, workers):
    start = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(match, tasks):
            results.append(result)
            if len(results) % 40 == 0:
                print(
                    f"{len(results)}/{len(tasks)} matches, "
                    f"{time.monotonic() - start:.1f}s",
                    flush=True,
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")
    return results


def screening_ranking(results):
    """Rank candidates by mean win rate in the 'a' seat against the panel."""
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


def ranking(results):
    """Rank by mean win rate over both seats; use for round robins."""
    totals, counts, specs = Counter(), Counter(), {}
    for result in results:
        for side, score in (("a", result["rate"]), ("b", 1 - result["rate"])):
            key = json.dumps(result[side], sort_keys=True)
            totals[key] += score
            counts[key] += 1
            specs[key] = result[side]
    return [
        (totals[k] / counts[k], specs[k])
        for k in sorted(totals, key=lambda k: -totals[k] / counts[k])
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=["smoke", "search", "tournament", "validate"]
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path(".context/groundskeeper-search.json")
    )
    parser.add_argument("--games", type=int, default=40)
    parser.add_argument("--finalists", type=int, default=8)
    parser.add_argument("--workers", type=int, default=0)
    args = parser.parse_args()
    if args.mode == "tournament" and args.input is None:
        parser.error("tournament mode needs --input, the search mode's output")
    workers = args.workers or None

    if args.mode == "smoke":
        print(json.dumps(match((ENGINE, MONEY, 8, 100)), indent=2))
        return

    if args.mode == "search":
        tasks = [
            (a, b, args.games, 1000 + 100 * i + 20 * j)
            for i, a in enumerate(candidates())
            for j, b in enumerate(PANEL)
        ]
        results = run(tasks, args.output, workers)
        for rate, spec in screening_ranking(results)[:15]:
            print(f"{rate:.3f}  {json.dumps(spec, sort_keys=True)}")
        return

    if args.mode == "validate":
        # Fresh seeds, the frozen winner, both seats, one match per opponent.
        opponents = [
            ("Runner-up: Margrave/Library money", RUNNER_UP),
            ("Third: three Margraves, early green", THIRD),
            ("Same engine without Monument", NO_MONUMENT),
            ("Groundskeeper engine", ENGINE),
            ("Monument money", MONUMENT_MONEY),
            ("Margrave money", MARGRAVE_MONEY),
            ("Treasure-only money", MONEY),
        ]
        tasks = [
            (WINNER, spec, args.games, 900000 + 1000 * i)
            for i, (_, spec) in enumerate(opponents)
        ]
        results = run(tasks, args.output, workers)
        for (label, _), result in zip(opponents, results):
            print(
                f"{result['rate']:.3f}  {result['wins']}W/{result['ties']}T "
                f"of {result['games']}  turns {result['turns']:.1f}  "
                f"score {result['scores'][0]:.1f} vs {result['scores'][1]:.1f}"
                f"  | {label}"
            )
        total = sum(r["wins"] + r["ties"] / 2 for r in results)
        played = sum(r["games"] for r in results)
        print(f"\noverall {total / played:.3f} over {played} games")
        print(f"turn-limit truncations: {sum(r['truncated'] for r in results)}")
        return

    ordered = screening_ranking(json.loads(args.input.read_text()))
    finalists = [spec for _, spec in ordered[: args.finalists]]
    # Keep the panel in the final so the winner has to beat plain money too.
    for spec in PANEL:
        if spec not in finalists:
            finalists.append(spec)
    tasks = [
        (a, b, args.games, 50000 + 100 * i + 20 * j)
        for i, a in enumerate(finalists)
        for j, b in enumerate(finalists)
        if i < j
    ]
    results = run(tasks, args.output, workers)
    for rate, spec in ranking(results):
        print(f"{rate:.3f}  {json.dumps(spec, sort_keys=True)}")


if __name__ == "__main__":
    main()
