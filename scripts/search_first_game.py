"""Hand-variant search on the base-set First Game board (boards/calibration/first_game.txt).

Round-robin between parameterised money/engine variants with paired seats
(each shuffle seed is played in both starting seats; ties earn half a win).
Run from the repository root with PYTHONPATH=.

    PYTHONPATH=. python scripts/search_first_game.py --stage 1   # 21 archetype variants
    PYTHONPATH=. python scripts/search_first_game.py --stage 2   # local search around Double Militia
    PYTHONPATH=. python scripts/search_first_game.py --stage 3   # Market / Militia cap sweep
    PYTHONPATH=. python scripts/search_first_game.py --stage 4   # 1,000-game finalist round robin

Pass --checkpoint <file> to save finished matchups and resume after an interruption.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
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
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

BOARD = load_board("boards/calibration/first_game.txt")

DEFAULT = dict(
    smithy=2, militia=1, market=0, village=0, merchant=0, remodel=0, mine=0,
    cellar=0, moat=0, workshop=0, duchy_gate=4, estate_gate=2,
    militia_first=False, play_militia_first=False, market_over_gold=False,
    village_per_smithy=0, remodel_gold_gate=0, early_only=None, silver_before_terminal_when=None,
)


class FirstGameVariant(EnhancedStrategy):
    def __init__(self, **spec):
        super().__init__()
        s = {**DEFAULT, **spec}
        self.spec = s
        self.name = "FG " + " ".join(f"{k}={v}" for k, v in spec.items()) if spec else "FG default"
        cap = PriorityRule.max_in_deck

        gain = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", s["duchy_gate"])),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", s["estate_gate"])),
        ]
        fives = []
        if s["market"]:
            fives.append(PriorityRule("Market", cap("Market", s["market"])))
        if s["mine"]:
            fives.append(PriorityRule("Mine", cap("Mine", s["mine"])))
        if s["market_over_gold"]:
            gain += fives + [PriorityRule("Gold")]
        else:
            gain += [PriorityRule("Gold")] + fives

        def early(rule_card, cond):
            if s["early_only"] is not None:
                cond = PriorityRule.and_(cond, PriorityRule.turn_number("<=", s["early_only"]))
            return PriorityRule(rule_card, cond)

        smithy_cond = cap("Smithy", s["smithy"])
        if s["village_per_smithy"]:
            # Engine: keep villages >= smithies - 1 before adding more Smithies.
            smithy_cond = PriorityRule.and_(
                smithy_cond,
                PriorityRule.deck_count_diff("Smithy", "Village", "<=", 0),
            )
        fours = []
        if s["smithy"]:
            fours.append(early("Smithy", smithy_cond))
        if s["militia"]:
            fours.append(early("Militia", cap("Militia", s["militia"])))
        if s["militia_first"]:
            fours.reverse()
        if s["remodel"]:
            fours.append(early("Remodel", cap("Remodel", s["remodel"])))
        gain += fours
        if s["village"]:
            gain.append(PriorityRule("Village", cap("Village", s["village"])))
        if s["merchant"]:
            gain.append(early("Merchant", cap("Merchant", s["merchant"])))
        if s["workshop"]:
            gain.append(early("Workshop", cap("Workshop", s["workshop"])))
        gain.append(PriorityRule("Silver"))
        if s["cellar"]:
            gain.append(early("Cellar", cap("Cellar", s["cellar"])))
        if s["moat"]:
            gain.append(early("Moat", cap("Moat", s["moat"])))
        self.gain_priority = gain

        terminals = [PriorityRule("Smithy"), PriorityRule("Militia")]
        if s["play_militia_first"]:
            terminals.reverse()
        self.action_priority = [
            PriorityRule("Village"),
            PriorityRule("Market"),
            PriorityRule("Merchant"),
            PriorityRule("Cellar"),
            PriorityRule("Remodel", PriorityRule.or_(
                PriorityRule.card_in_hand("Estate"),
                PriorityRule.and_(PriorityRule.card_in_hand("Gold"),
                                  PriorityRule.provinces_left("<=", s["remodel_gold_gate"])),
            )),
        ] + terminals + [
            PriorityRule("Mine"),
            PriorityRule("Moat"),
            PriorityRule("Workshop"),
        ]
        self.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Gold", PriorityRule.provinces_left("<=", s["remodel_gold_gate"])),
            PriorityRule("Copper"),
        ]

    def choose_mine_treasure(self, state, player, choices):
        for name in ("Silver", "Copper"):
            for c in choices:
                if c.name == name:
                    return c
        return None


def make(spec):
    return FirstGameVariant(**spec)


def match(task):
    a, b, games, seed = task
    if games % 2:
        raise ValueError("games must be even so every seed is played in both seats")
    outcomes = []
    totals = Counter()
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [GeneticAI(make(a)), GeneticAI(make(b))]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(ais, [get_card(n) for n in BOARD.kingdom_cards])
        player = state.players[i % 2]
        opponent = state.players[1 - i % 2]
        while not state.is_game_over() and state.turn_number < 160:
            state.play_turn()
        key = lambda p: (p.get_victory_points(), -p.turns_taken)
        score = 1.0 if key(player) > key(opponent) else 0.5 if key(player) == key(opponent) else 0.0
        outcomes.append(score)
        totals["turns"] += state.turn_number
        totals["score"] += player.get_victory_points()
        totals["opponent_score"] += opponent.get_victory_points()
    rate = statistics.mean(outcomes)
    pairs = [statistics.mean(outcomes[i : i + 2]) for i in range(0, games, 2)]
    se = statistics.stdev(pairs) / (len(pairs) ** 0.5) if len(pairs) > 1 else 0
    return dict(a=a, b=b, games=games, seed=seed, rate=rate,
                paired_ci95=[max(0, rate - 1.96 * se), min(1, rate + 1.96 * se)], totals=dict(totals))


def _task_key(task):
    a, b, games, seed = task
    return json.dumps([a, b, games, seed], sort_keys=True)


def round_robin(specs, games, seed, workers, checkpoint=None):
    tasks = [(a, b, games, seed) for a, b in itertools.combinations(specs, 2)]
    t0 = time.time()
    done = {}
    if checkpoint and Path(checkpoint).exists():
        for line in Path(checkpoint).read_text().splitlines():
            r = json.loads(line)
            done[_task_key((r["a"], r["b"], r["games"], r["seed"]))] = r
    todo = [t for t in tasks if _task_key(t) not in done]
    print(f"{len(done)} matchups cached, {len(todo)} to run", flush=True)
    results = [done[_task_key(t)] for t in tasks if _task_key(t) in done]
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("fork")) as ex:
        for r in ex.map(match, todo):
            results.append(r)
            if checkpoint:
                with open(checkpoint, "a") as fh:
                    fh.write(json.dumps(r) + "\n")
    names = [make(s).name for s in specs]
    idx = {json.dumps(s, sort_keys=True): i for i, s in enumerate(specs)}
    n = len(specs)
    grid = [[None] * n for _ in range(n)]
    for r in results:
        i, j = idx[json.dumps(r["a"], sort_keys=True)], idx[json.dumps(r["b"], sort_keys=True)]
        grid[i][j] = r["rate"]
        grid[j][i] = 1 - r["rate"]
    avg = [statistics.mean(x for x in row if x is not None) for row in grid]
    order = sorted(range(n), key=lambda i: -avg[i])
    print(f"\n{len(tasks)} matchups x {games} games in {time.time()-t0:.0f}s")
    for i in order:
        print(f"{avg[i]*100:5.1f}%  {names[i]}")
    return dict(names=names, grid=grid, avg=avg, results=results)


STAGE1 = [
    dict(smithy=0, militia=0),
    dict(smithy=1, militia=0),
    dict(smithy=2, militia=0),
    dict(smithy=0, militia=1),
    dict(smithy=0, militia=2),
    dict(smithy=1, militia=1),
    dict(smithy=2, militia=1),
    dict(smithy=2, militia=1, militia_first=True),
    dict(smithy=2, militia=2),
    dict(smithy=1, militia=2),
    dict(smithy=2, militia=1, market=1),
    dict(smithy=2, militia=1, market=2),
    dict(smithy=2, militia=1, merchant=1),
    dict(smithy=2, militia=1, cellar=1),
    dict(smithy=2, militia=1, moat=1),
    dict(smithy=2, militia=1, remodel=1, remodel_gold_gate=4),
    dict(smithy=2, militia=1, mine=1),
    dict(smithy=2, militia=1, workshop=1),
    dict(smithy=3, militia=1, village=2, village_per_smithy=1, market=2),
    dict(smithy=4, militia=1, village=4, village_per_smithy=1, market=3, remodel=1, remodel_gold_gate=4),
    dict(smithy=3, militia=2, village=3, village_per_smithy=1, market=2, market_over_gold=True),
]

STAGE2 = [
    {'smithy': 0, 'militia': 2},
    {'smithy': 0, 'militia': 3},
    {'smithy': 0, 'militia': 2, 'market': 1},
    {'smithy': 0, 'militia': 2, 'market': 2},
    {'smithy': 1, 'militia': 2},
    {'smithy': 1, 'militia': 2, 'market': 1},
    {'smithy': 0, 'militia': 2, 'cellar': 1},
    {'smithy': 0, 'militia': 2, 'moat': 1},
    {'smithy': 0, 'militia': 2, 'merchant': 1},
    {'smithy': 0, 'militia': 2, 'mine': 1},
    {'smithy': 0, 'militia': 2, 'duchy_gate': 3},
    {'smithy': 0, 'militia': 2, 'duchy_gate': 5},
    {'smithy': 0, 'militia': 2, 'duchy_gate': 5, 'estate_gate': 3},
    {'smithy': 0, 'militia': 2, 'estate_gate': 3},
    {'smithy': 0, 'militia': 2, 'early_only': 10},
    {'smithy': 0, 'militia': 2, 'market': 1, 'duchy_gate': 5},
    {'smithy': 0, 'militia': 3, 'market': 1},
    {'smithy': 0, 'militia': 1, 'market': 2},
    {'smithy': 1, 'militia': 1, 'market': 1},
    {'smithy': 0, 'militia': 2, 'market': 1, 'cellar': 1},
]

STAGE3 = [
    {'smithy': 2, 'militia': 1},
    {'smithy': 0, 'militia': 2, 'market': 2},
    {'smithy': 0, 'militia': 2, 'market': 3},
    {'smithy': 0, 'militia': 2, 'market': 4},
    {'smithy': 0, 'militia': 3, 'market': 2},
    {'smithy': 0, 'militia': 3, 'market': 3},
    {'smithy': 0, 'militia': 2, 'market': 2, 'duchy_gate': 5},
    {'smithy': 0, 'militia': 2, 'market': 2, 'cellar': 1},
    {'smithy': 0, 'militia': 2, 'market': 2, 'moat': 1},
    {'smithy': 0, 'militia': 2, 'market': 2, 'merchant': 1},
    {'smithy': 0, 'militia': 1, 'market': 3},
    {'smithy': 1, 'militia': 2, 'market': 2},
    {'smithy': 0, 'militia': 2, 'market': 2, 'market_over_gold': True},
    {'smithy': 0, 'militia': 2, 'market': 2, 'estate_gate': 3},
    {'smithy': 0, 'militia': 2, 'market': 2, 'early_only': 12},
    {'smithy': 0, 'militia': 2, 'market': 2, 'mine': 1},
    {'smithy': 0, 'militia': 3, 'market': 2, 'duchy_gate': 5},
]

STAGE4 = [
    {'smithy': 0, 'militia': 0},
    {'smithy': 2, 'militia': 1},
    {'smithy': 0, 'militia': 2},
    {'smithy': 0, 'militia': 2, 'market': 2},
    {'smithy': 0, 'militia': 3, 'market': 2},
    {'smithy': 0, 'militia': 3, 'market': 3},
    {'smithy': 0, 'militia': 2, 'market': 2, 'moat': 1},
]

STAGES = {"1": STAGE1, "2": STAGE2, "3": STAGE3, "4": STAGE4}
STAGE_DEFAULTS = {"1": (200, 1000), "2": (200, 2000), "3": (200, 3000), "4": (1000, 4000)}


def _even_games(value: str) -> int:
    games = int(value)
    if games <= 0 or games % 2:
        raise argparse.ArgumentTypeError(
            f"--games must be a positive even number so every seed is played in both seats, got {value}"
        )
    return games


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="1")
    ap.add_argument("--games", type=_even_games, help="Even number; default 200 (stages 1-3) or 1000 (stage 4)")
    ap.add_argument("--seed", type=int, help="Default: 1000 x stage")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--specs", help="JSON file with a list of specs (overrides --stage)")
    ap.add_argument("--output")
    ap.add_argument("--checkpoint", help="JSON-lines file of finished matchups; reruns skip them")
    args = ap.parse_args()
    specs = json.loads(Path(args.specs).read_text()) if args.specs else STAGES[args.stage]
    default_games, default_seed = STAGE_DEFAULTS.get(args.stage, (200, 1000))
    games = default_games if args.games is None else args.games
    seed = default_seed if args.seed is None else args.seed
    out = round_robin(specs, games, seed, args.workers, args.checkpoint)
    if args.output:
        Path(args.output).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
