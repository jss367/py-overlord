"""Reproduce the finalist tournament and independent validation for this board.

Run from the repository root with PYTHONPATH=.
Ties earn half a win; each shuffle seed is played in both starting seats.
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
from dominion.projects.registry import get_project
from dominion.prophecies.registry import get_prophecy
from generated_strategies.tea_house_kind_emperor import TeaHouseEmperor

BOARD = load_board("boards/tea_house_kind_emperor.txt")


class Money(TeaHouseEmperor):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode

    def choose_gain(self, s, p, choices):
        c = Counter(x.name for x in p.all_cards())
        names = ["Province"]
        if s.supply["Province"] <= 4:
            names += ["Duke", "Duchy"] if c["Duchy"] >= 4 else ["Duchy", "Duke"]
        if s.supply["Province"] <= 1:
            names.append("Estate")
        if self.mode == "Duke" and p.turns_taken >= 7:
            names += (
                ["Duke", "Duchy"]
                if c["Duchy"] >= 4 and c["Duke"] < c["Duchy"] - 2
                else ["Duchy", "Duke"]
            )
        if self.mode == "Guildhall" and not p.projects:
            names.append("Guildhall")
        if self.mode in ["Guildhall", "Buried Treasure"] and c["Buried Treasure"] < 4:
            names.append("Buried Treasure")
        if (
            self.mode in ["Imperial Envoy", "Mine", "Fortune Hunter"]
            and c[self.mode] < 2
        ):
            names.append(self.mode)
        names += ["Gold", "Silver"]
        return self.pick(choices, names)


def make(spec):
    return Money(spec["money"]) if "money" in spec else TeaHouseEmperor(**spec)


def match(task):
    a, b, games, seed = task
    score = wins = ties = truncated = 0
    lengths, vps = [], []
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(make(a)), GeneticAI(make(b))]
        if i % 2:
            ais.reverse()
        s = GameState(players=[], supply={})
        s.log_callback = lambda *_: None
        s.initialize_game(
            ais,
            [get_card(n) for n in BOARD.kingdom_cards],
            projects=[get_project("Guildhall")],
            prophecy=get_prophecy("Kind Emperor"),
        )
        while not s.is_game_over() and s.turn_number < 160:
            s.play_turn()
        truncated += not s._normal_game_end_reached()
        players = s.players if i % 2 == 0 else list(reversed(s.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        win = 1 if keys[0] > keys[1] else 0.5 if keys[0] == keys[1] else 0
        score += win
        wins += win == 1
        ties += win == 0.5
        lengths.append(s.turn_number)
        vps.append([k[0] for k in keys])
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        wins=wins,
        ties=ties,
        rate=score / games,
        turns=sum(lengths) / games,
        scores=[sum(x[j] for x in vps) / games for j in [0, 1]],
        truncated=truncated,
    )


def run(tasks, path):
    start = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=6) as pool:
        for r in pool.map(match, tasks):
            results.append(r)
            if len(results) % 20 == 0:
                print(
                    f"{len(results)}/{len(tasks)} matchups, {time.time() - start:.1f}s",
                    flush=True,
                )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(results, indent=2) + "\n")
    return results


FINALISTS = [
    dict(opening="Fortune Hunter", green=2, envoy=2),
    dict(opening="Fortune Hunter", green=3, envoy=2),
    dict(opening="Fortune Hunter", green=3, envoy=2, buried=1),
    dict(opening="Fortune Hunter", green=1, envoy=2),
    dict(opening="Fortune Hunter", green=3, envoy=1),
    dict(opening="Courier", green=2, envoy=2),
    dict(opening="Fortune Hunter", green=2, mastermind=2),
    dict(opening="Fortune Hunter", green=2, free="city"),
]
CHAMPION = dict(opening="Fortune Hunter", green=1, envoy=2)
VALIDATION_PANEL = [
    dict(opening="Fortune Hunter", green=2, envoy=2),
    dict(opening="Courier", green=2, envoy=2),
    dict(opening="Fortune Hunter", green=2, mastermind=2),
    dict(opening="Fortune Hunter", green=2, envoy=2, scoring="Duke"),
    dict(guildhall=True, buried=4),
    {"money": "Imperial Envoy"},
    {"money": "Big Money"},
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["tournament", "validation", "smoke"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "smoke":
        print(
            json.dumps(match((CHAMPION, {"money": "Imperial Envoy"}, 4, 100)), indent=2)
        )
        return
    if args.mode == "tournament":
        tasks = [
            (a, b, 400, 30000 + 1000 * i)
            for i, (a, b) in enumerate(itertools.combinations(FINALISTS, 2))
        ]
    else:
        tasks = [
            (CHAMPION, b, 1000, 100000 + 2000 * i)
            for i, b in enumerate(VALIDATION_PANEL)
        ]
    path = args.output or Path(f"docs/analysis/tea_house_kind_emperor_{args.mode}.json")
    results = run(tasks, path)
    print(json.dumps(results, indent=2))
    if any(r["truncated"] for r in results):
        raise RuntimeError(
            "Turn-limit truncations occurred; results require inspection"
        )


if __name__ == "__main__":
    main()
