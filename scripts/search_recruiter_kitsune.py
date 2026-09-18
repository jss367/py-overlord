"""Seeded, seat-balanced search on the fixed Recruiter / Kitsune board."""

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
from dominion.prophecies.registry import get_prophecy
from dominion.strategy.strategies.recruiter_kitsune import DEFAULTS, RecruiterKitsune
from dominion.strategy.strategy_loader import StrategyLoader


BOARD_PATH = "boards/recruiter_kitsune.txt"
MONEY = DEFAULTS | {k: 0 for k in (
    "recruiter", "kitsune", "inventor", "treasurer", "villa", "village",
    "courtyard", "counterfeit", "anvil", "engineer",
)} | dict(silver=99, gold=99, green=0, opening="Silver", first_five="Gold", build="money")
KITSUNE_MONEY = MONEY | dict(kitsune=2, courtyard=1, recruiter=1, first_five="Kitsune")
DRAW_ENGINE = dict(DEFAULTS)
GAIN_ENGINE = DEFAULTS | dict(inventor=5, courtyard=5, villa=4, build="gain", green=12)
PANEL = [MONEY, KITSUNE_MONEY, DRAW_ENGINE, GAIN_ENGINE]


def make_strategy(spec):
    if "registered" in spec:
        strategy = StrategyLoader().get_strategy(spec["registered"])
        if strategy is None:
            raise ValueError(spec)
        return strategy
    return RecruiterKitsune(**spec)


def match(task):
    a, b, games, seed = task
    board = load_board(BOARD_PATH)
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
        state.initialize_game(ais, [get_card(n) for n in board.kingdom_cards], prophecy=get_prophecy(board.prophecy))
        while not state.is_game_over() and state.turn_number < 120:
            state.play_turn()
        truncated += not state._normal_game_end_reached()
        players = state.players if i % 2 == 0 else list(reversed(state.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        wins += keys[0] > keys[1]
        ties += keys[0] == keys[1]
        turns += sum(p.turns_taken for p in players) / 2
        endings["Province" if state.supply["Province"] == 0 else "three piles" if state._normal_game_end_reached() else "turn limit"] += 1
        for j, p in enumerate(players):
            points[j] += keys[j][0]
            decks[j].update(c.name for c in p.all_cards())
    return dict(a=a, b=b, games=games, seed=seed, wins=wins, ties=ties,
                rate=(wins + ties / 2) / games, mean_turns_per_player=turns / games,
                points=[x / games for x in points], truncated=truncated,
                endings=dict(endings), decks=[{k: round(v / games, 3) for k, v in sorted(d.items())} for d in decks])


def unique(specs):
    return list({json.dumps(s, sort_keys=True): s for s in specs}.values())


def candidates():
    specs = PANEL + [
        DEFAULTS | dict(opening=o, first_five=f, build=b)
        for o, f, b in itertools.product(
            ("Silver", "Inventor", "Engineer", "Anvil"),
            ("Recruiter", "Kitsune", "Treasurer"), ("draw", "gain"))
    ]
    rng = random.Random(20260917)
    for _ in range(64):
        specs.append(DEFAULTS | dict(
            recruiter=rng.choice([0, 1, 1, 2]), kitsune=rng.choice([0, 1, 2, 3]),
            inventor=rng.choice([0, 1, 2, 3, 5]), treasurer=rng.choice([0, 1, 2, 3]),
            villa=rng.choice([0, 1, 2, 4]), village=rng.choice([0, 0, 1, 2]),
            courtyard=rng.choice([1, 2, 3, 4, 6]), counterfeit=rng.choice([0, 0, 1, 2]),
            anvil=rng.choice([0, 0, 1, 2]), engineer=rng.choice([0, 0, 1, 2]),
            silver=rng.choice([1, 2, 3, 99]), gold=rng.choice([0, 1, 2, 4, 99]),
            green=rng.choice([0, 6, 8, 10, 12]), duchy=rng.choice([2, 3, 4]),
            opening=rng.choice(["Silver", "Courtyard", "Inventor", "Engineer", "Anvil"]),
            first_five=rng.choice(["Recruiter", "Kitsune", "Treasurer"]),
            build=rng.choice(["draw", "gain", "money"]),
            engineer_trash=rng.choice([False, True]), key_first=rng.choice([False, True]),
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
    for base in leaders[:3]:
        for key, values in dict(
            inventor=[0, 2, 4, 6], courtyard=[2, 4, 6, 8], kitsune=[0, 1, 2, 3],
            treasurer=[0, 1, 2, 3], recruiter=[0, 1, 2], green=[0, 6, 10, 14],
            opening=["Silver", "Courtyard", "Inventor", "Engineer"],
            first_five=["Recruiter", "Kitsune", "Treasurer"],
            build=["draw", "gain", "money"], anvil=[0, 1], counterfeit=[0, 1],
        ).items():
            specs.extend(base | {key: value} for value in values)
    return unique(specs)


def run(tasks, path, workers, mode):
    start = time.monotonic()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(match, tasks):
            results.append(result)
            if len(results) % 25 == 0:
                print(f"{len(results)}/{len(tasks)} matches, {time.monotonic() - start:.1f}s", flush=True)
    output = dict(mode=mode, board=BOARD_PATH, prophecy="Great Leader",
                  games=sum(r["games"] for r in results), truncated=sum(r["truncated"] for r in results),
                  elapsed_seconds=time.monotonic() - start, results=results,
                  ranking=ranking(results, both=mode == "tournament"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n")
    for row in output["ranking"][:8]:
        print(f"{row['rate']:.3f} {json.dumps(row['spec'], sort_keys=True)}", flush=True)
    print(f"Saved {output['games']} games; {output['truncated']} truncated: {path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["smoke", "search", "refine", "tournament", "validate"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".context/recruiter-kitsune-search.json"))
    parser.add_argument("--games", type=int, default=24)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--finalists", type=int, default=10)
    args = parser.parse_args()
    if args.games < 2 or args.games % 2:
        parser.error("--games must be a positive even count for seat balance")
    if args.mode == "smoke":
        print(json.dumps(match((DRAW_ENGINE, KITSUNE_MONEY, 8, 100)), indent=2))
        return
    if args.mode == "search":
        tasks = [(a, b, args.games, 100000 + j * 10000) for a in candidates() for j, b in enumerate(PANEL)]
    else:
        if args.input is None:
            parser.error("this mode requires --input")
        previous = json.loads(args.input.read_text())
        leaders = [r["spec"] for r in previous["ranking"][:args.finalists]]
        if args.mode == "refine":
            opponents = unique(leaders[:3] + [KITSUNE_MONEY])
            tasks = [(a, b, args.games, 300000 + j * 10000) for a in refinement(leaders) for j, b in enumerate(opponents)]
        elif args.mode == "tournament":
            finalists = unique(leaders + PANEL)
            tasks = [(a, b, args.games, 500000 + i * 10000) for i, (a, b) in enumerate(itertools.combinations(finalists, 2))]
        else:
            winner = leaders[0]
            opponents = unique(leaders[1:5] + PANEL + [
                winner | {"inventor": 0}, winner | {"kitsune": 0, "first_five": "Recruiter"},
                {"registered": "Big Money"}, {"registered": "Courtyard Money"},
            ])
            tasks = [(winner, b, args.games, 3000000 + i * 10000) for i, b in enumerate(opponents)]
    run(tasks, args.output, args.workers, args.mode)


if __name__ == "__main__":
    main()
