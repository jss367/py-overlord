"""Seeded, seat-balanced policy search on the fixed Suzhou board.

Modes
-----
``smoke``       one match, to check the harness runs.
``search``      broad screen of every candidate against a fixed panel.
``nogk``        the same screen restricted to Groundskeeper-free plans, which
                supplies the yardstick the winner has to beat.
``refine``      one-field sweeps around the screen's leaders.
``tournament``  seat-balanced round robin among the finalists.
``validate``    the winner against the finalists, the panel, its own
                one-field ablations and the registered generalists.

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
from dominion.strategy.strategies.suzhou_groundskeeper import (
    CARD_KEYS,
    DEFAULTS,
    WINNER,
    SuzhouGroundskeeper,
)
from dominion.strategy.strategy_loader import StrategyLoader


BOARD_PATH = "boards/suzhou.txt"
TURN_LIMIT = 120

#: Panel: plain money, the best non-Groundskeeper engine shapes, and the
#: Groundskeeper engine the knobs default to.
EMPTY = {key: 0 for key in CARD_KEYS.values()}
MONEY = DEFAULTS | EMPTY | dict(
    silver=99, gold=99, green=10, opening="Silver", green_gate=0,
    estate_vp=False,
)
LAB_MONEY = MONEY | dict(laboratory=4, market=2, silver=3, opening="Silver")
IRONWORKS_GREEN = DEFAULTS | dict(
    groundskeeper=0, ironworks=4, bridge=2, village=3, crossroads=3,
    laboratory=2, market=2, great_hall=99, mill=4, green=10,
    green_gate=0, estate_vp=False, opening="Ironworks",
)
GROUNDSKEEPER = dict(DEFAULTS)
#: The frozen recommendation, re-exported so tests can replay it by seed.
WINNER_SPEC = dict(WINNER)
PANEL = [MONEY, LAB_MONEY, IRONWORKS_GREEN, GROUNDSKEEPER]


def make_strategy(spec):
    """A parameter dict, or ``{"registered": name}`` for a catalog entry."""

    if "registered" in spec:
        strategy = StrategyLoader().get_strategy(spec["registered"])
        if strategy is None:
            raise ValueError(f"No registered strategy named {spec['registered']!r}")
        return strategy
    return SuzhouGroundskeeper(**spec)


def match(task):
    """Play ``games`` seat-alternating games between two strategy specs."""

    a, b, games, seed = task
    board = load_board(BOARD_PATH)
    kingdom = [get_card(name) for name in board.kingdom_cards]
    wins = ties = truncated = 0
    turns = 0
    points = [0, 0]
    tokens = [0, 0]
    decks = [Counter(), Counter()]
    endings = Counter()
    emptied = Counter()
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(make_strategy(a)), GeneticAI(make_strategy(b))]
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
        turns += sum(p.turns_taken for p in players) / 2
        emptied.update(name for name, count in state.supply.items() if count <= 0)
        endings[
            "Province"
            if state.supply["Province"] == 0
            else "three piles"
            if state._normal_game_end_reached()
            else "turn limit"
        ] += 1
        for j, player in enumerate(players):
            points[j] += keys[j][0]
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
        mean_turns_per_player=turns / games,
        points=[value / games for value in points],
        vp_tokens=[value / games for value in tokens],
        truncated=truncated,
        endings=dict(endings),
        emptied_piles={k: round(v / games, 3) for k, v in emptied.most_common()},
        decks=[{k: round(v / games, 3) for k, v in sorted(d.items())} for d in decks],
    )


def unique(specs):
    return list({json.dumps(s, sort_keys=True): s for s in specs}.values())


def sweep(rng, groundskeeper_values):
    return DEFAULTS | dict(
        groundskeeper=rng.choice(groundskeeper_values),
        ironworks=rng.choice([0, 1, 2, 3, 4, 5]),
        crossroads=rng.choice([0, 1, 2, 3, 4]),
        laboratory=rng.choice([0, 1, 2, 3, 4]),
        market=rng.choice([0, 1, 2, 3]),
        nobles=rng.choice([0, 0, 1, 2]),
        great_hall=rng.choice([0, 2, 4, 99]),
        mill=rng.choice([0, 2, 4, 99]),
        bridge=rng.choice([0, 1, 2, 3]),
        village=rng.choice([0, 1, 2, 3, 4]),
        silver=rng.choice([0, 1, 2, 3, 99]),
        gold=rng.choice([0, 2, 3, 99]),
        green=rng.choice([6, 8, 10, 12, 14]),
        duchy=rng.choice([2, 3, 4, 6]),
        estate_vp=rng.choice([False, True]),
        green_gate=rng.choice([0, 1, 2]),
        opening=rng.choice(["Silver", "Ironworks", "Mill", "Crossroads", "Great Hall"]),
    )


def candidates(groundskeeper=True):
    """Named theories first, then a seeded random sweep around them."""

    values = [0, 1, 2, 3, 4, 5] if groundskeeper else [0]
    specs = list(PANEL) if groundskeeper else [MONEY, LAB_MONEY, IRONWORKS_GREEN]

    if groundskeeper:
        # How many Groundskeepers does the engine want, and how fast should it
        # turn the corner?
        for count, green in itertools.product((1, 2, 3, 4), (8, 10, 12)):
            specs.append(GROUNDSKEEPER | dict(groundskeeper=count, green=green))
        # How much Bridge does mass greening want?
        for bridge, market in itertools.product((0, 1, 2, 3), (1, 3)):
            specs.append(GROUNDSKEEPER | dict(bridge=bridge, market=market))
        # Is holding the green back until the Groundskeepers are out worth it?
        for green_gate, estate_vp in itertools.product((0, 1, 2), (False, True)):
            specs.append(GROUNDSKEEPER | dict(green_gate=green_gate, estate_vp=estate_vp))
    else:
        for ironworks, great_hall in itertools.product((2, 4), (0, 99)):
            specs.append(IRONWORKS_GREEN | dict(ironworks=ironworks, great_hall=great_hall))
        for bridge, village in itertools.product((0, 2), (0, 3)):
            specs.append(IRONWORKS_GREEN | dict(bridge=bridge, village=village))
        for laboratory, market in itertools.product((2, 4), (0, 2)):
            specs.append(LAB_MONEY | dict(laboratory=laboratory, market=market))

    rng = random.Random(20260917)
    for _ in range(140 if groundskeeper else 80):
        specs.append(sweep(rng, values))
    return unique(specs)


def ranking(results, both=False):
    scores, games, specs = Counter(), Counter(), {}
    for result in results:
        sides = [("a", result["wins"] + result["ties"] / 2)]
        if both:
            sides.append(("b", result["games"] - result["wins"] - result["ties"] / 2))
        for side, score in sides:
            key = json.dumps(result[side], sort_keys=True)
            specs[key] = result[side]
            scores[key] += score
            games[key] += result["games"]
    return [
        dict(rate=scores[key] / games[key], games=games[key], spec=specs[key])
        for key in sorted(scores, key=lambda k: (-scores[k] / games[k], k))
    ]


def refinement(leaders):
    specs = list(leaders)
    knobs = dict(
        groundskeeper=[0, 1, 2, 3, 4, 5],
        ironworks=[1, 2, 3, 4, 5],
        crossroads=[0, 1, 2, 3, 4],
        laboratory=[0, 1, 2, 3, 4],
        market=[0, 1, 2, 3],
        nobles=[0, 1, 2],
        great_hall=[0, 2, 4, 99],
        mill=[0, 2, 4, 99],
        bridge=[0, 1, 2, 3],
        village=[0, 1, 2, 3, 4],
        silver=[0, 1, 2, 3],
        gold=[0, 2, 3, 99],
        green=[6, 8, 10, 12, 14],
        duchy=[2, 3, 4, 6],
        estate_vp=[False, True],
        green_gate=[0, 1, 2],
        opening=["Silver", "Ironworks", "Mill", "Crossroads", "Great Hall"],
    )
    for base in leaders[:3]:
        for key, values in knobs.items():
            specs.extend(base | {key: value} for value in values)
    return unique(specs)


def ablations(winner):
    """One change of claim per row: this deck does not buy card X.

    Zeroing a deck cap is not enough when the plan also opens on that card,
    because the opening rule buys it regardless of the cap. Where the two
    name the same pile the opener is cleared with it, so the row measures a
    deck that really never gains the card.
    """

    def without(key):
        spec = winner | {key: 0}
        if CARD_KEYS.get(winner["opening"]) == key:
            spec["opening"] = ""
        return spec

    specs = [without("groundskeeper")]
    for key in ("ironworks", "crossroads", "great_hall", "mill", "bridge", "laboratory"):
        if winner[key]:
            specs.append(without(key))
    specs.append(winner | {"estate_vp": not winner["estate_vp"]})
    for value in (0, 1, 2):
        if value != winner["green_gate"]:
            specs.append(winner | {"green_gate": value})
    return unique(specs)


def run(tasks, path, workers, mode, extra=None):
    start = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(match, tasks):
            results.append(result)
            if len(results) % 25 == 0:
                print(
                    f"{len(results)}/{len(tasks)} matches, "
                    f"{time.monotonic() - start:.1f}s",
                    flush=True,
                )
    output = dict(
        mode=mode,
        board=BOARD_PATH,
        games=sum(r["games"] for r in results),
        truncated=sum(r["truncated"] for r in results),
        elapsed_seconds=time.monotonic() - start,
        results=results,
        ranking=ranking(results, both=mode == "tournament"),
    )
    if extra:
        output.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n")
    for row in output["ranking"][:8]:
        print(f"{row['rate']:.3f} {json.dumps(row['spec'], sort_keys=True)}", flush=True)
    print(f"Saved {output['games']} games; {output['truncated']} truncated: {path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=["smoke", "search", "nogk", "refine", "tournament", "validate"],
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--yardstick", type=Path, help="a nogk run, for validate")
    parser.add_argument("--output", type=Path, default=Path(".context/suzhou-search.json"))
    parser.add_argument("--games", type=int, default=24)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--finalists", type=int, default=10)
    args = parser.parse_args()
    if args.games < 2 or args.games % 2:
        parser.error("--games must be a positive even count for seat balance")

    if args.mode == "smoke":
        print(json.dumps(match((GROUNDSKEEPER, IRONWORKS_GREEN, 8, 100)), indent=2))
        return
    if args.mode in ("search", "nogk"):
        pool = candidates(groundskeeper=args.mode == "search")
        seed = 100000 if args.mode == "search" else 200000
        tasks = [
            (a, b, args.games, seed + j * 1000)
            for a in pool
            for j, b in enumerate(PANEL)
        ]
        run(tasks, args.output, args.workers, args.mode)
        return

    if args.input is None:
        parser.error("this mode requires --input")
    previous = json.loads(args.input.read_text())
    leaders = [row["spec"] for row in previous["ranking"][: args.finalists]]

    if args.mode == "refine":
        opponents = unique(leaders[:3] + [IRONWORKS_GREEN])
        tasks = [
            (a, b, args.games, 300000 + j * 1000)
            for a in refinement(leaders)
            for j, b in enumerate(opponents)
        ]
        run(tasks, args.output, args.workers, args.mode)
        return

    if args.mode == "tournament":
        finalists = unique(leaders + PANEL)
        tasks = [
            (a, b, args.games, 500000 + i * 1000)
            for i, (a, b) in enumerate(itertools.combinations(finalists, 2))
        ]
        run(tasks, args.output, args.workers, args.mode)
        return

    winner = leaders[0]
    opponents = unique(
        leaders[1:5]
        + PANEL
        + ablations(winner)
        + [{"registered": "Big Money"}, {"registered": "Big Money Smithy"}]
    )
    no_groundskeeper = ablations(winner)[0]
    labels = {json.dumps(no_groundskeeper, sort_keys=True): "no Groundskeeper"}
    if args.yardstick:
        best_nogk = json.loads(args.yardstick.read_text())["ranking"][0]["spec"]
        opponents = unique(opponents + [best_nogk])
        labels[json.dumps(best_nogk, sort_keys=True)] = "best searched Groundskeeper-free plan"
    tasks = [
        (winner, b, args.games, 700000 + i * 1000) for i, b in enumerate(opponents)
    ]
    run(tasks, args.output, args.workers, args.mode, extra=dict(winner=winner, labels=labels))


if __name__ == "__main__":
    main()
