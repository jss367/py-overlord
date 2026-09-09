"""Kimberley (Mine / King's Court / Colony) search with paired seats and combo auditing.

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
import statistics
import time

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.landmarks.registry import get_landmark
from dominion.projects.registry import get_project
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from generated_strategies.kimberley_mine_engine import KimberleyMine, UPGRADE_TARGET

BOARD = load_board("boards/kimberley.txt")

SUPPORT_CAPS = {
    "Smithy": 2,
    "Laboratory": 3,
    "Mine": 2,
    "Priest": 1,
    "Market Square": 2,
    "Hoard": 2,
    "Bank": 2,
}


class Money(EnhancedStrategy):
    """Colony Big Money with one optional support card, as a fixed baseline."""

    def __init__(self, mode="plain"):
        super().__init__()
        self.mode = mode
        self.name = f"Colony Money ({mode})"
        self.action_priority = [PriorityRule(n) for n in SUPPORT_CAPS]
        self.treasure_priority = [
            PriorityRule(n) for n in ["Platinum", "Gold", "Hoard", "Silver", "Copper", "Bank"]
        ]
        self.trash_priority = [PriorityRule("Curse"), PriorityRule("Estate")]
        self.mine_gains = Counter()

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def choose_action(self, state, player, choices):
        usable = [
            c
            for c in choices
            if c is not None
            and not (c.name == "Mine" and not any(
                t.is_treasure and t.name in UPGRADE_TARGET for t in player.hand))
            and not (c.name == "Priest" and not any(
                t.name in ("Estate", "Curse") for t in player.hand))
        ]
        return self.pick(usable, list(SUPPORT_CAPS))

    def choose_mine_treasure(self, state, player, choices):
        usable = [
            c for c in choices
            if c.name in UPGRADE_TARGET and state.supply.get(UPGRADE_TARGET[c.name], 0)
        ]
        return self.pick(usable, ["Gold", "Silver", "Copper"])

    def choose_mine_gain(self, state, player, choices):
        return self.pick(choices, ["Platinum", "Gold", "Silver", "Copper"])

    def choose_gain(self, state, player, choices):
        available = {c.name: c for c in choices if c is not None}
        if state.phase != "buy" and available and all(
            c.is_treasure for c in available.values()
        ):
            return self.choose_mine_gain(state, player, choices)
        c = Counter(x.name for x in player.all_cards())
        colonies = state.supply.get("Colony", 0)
        names = ["Colony"]
        if colonies <= 4 or player.turns_taken >= 14:
            names.append("Province")
        names.append("Platinum")
        if colonies <= 2:
            names.append("Duchy")
        if colonies <= 1:
            names.append("Estate")
        support = self.mode in SUPPORT_CAPS and c[self.mode] < SUPPORT_CAPS[self.mode]
        # Hoard ($6) and Bank ($7) must outrank Gold or they are never bought.
        if support and self.mode in ("Hoard", "Bank"):
            names.append(self.mode)
        names.append("Gold")
        if support:
            names.append(self.mode)
        names.append("Silver")
        return self.pick(choices, names)


def make(spec):
    return Money(spec["money"]) if "money" in spec else KimberleyMine(**spec)


def match(task):
    a, b, games, seed = task
    outcomes = []
    totals = Counter()
    upgrades = Counter()
    multipliers = Counter()
    for i in range(games):
        random.seed(seed + i // 2)
        strategy = make(a)
        ais = [GeneticAI(strategy), GeneticAI(make(b))]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(
            ais,
            [get_card(n) for n in BOARD.kingdom_cards],
            projects=[get_project(n) for n in BOARD.projects],
            landmarks=[get_landmark(n) for n in BOARD.landmarks],
        )
        player = state.players[i % 2]
        opponent = state.players[1 - i % 2]
        first_platinum = None
        while not state.is_game_over() and state.turn_number < 160:
            active = state.current_player
            state.play_turn()
            if active is player and first_platinum is None and player.count("Platinum"):
                first_platinum = player.turns_taken
        key = lambda p: (p.get_victory_points(), -p.turns_taken)
        score = (
            1.0
            if key(player) > key(opponent)
            else 0.5
            if key(player) == key(opponent)
            else 0.0
        )
        outcomes.append(score)
        totals["wins"] += score == 1
        totals["ties"] += score == 0.5
        totals["truncated"] += not state._normal_game_end_reached()
        totals["max_turns"] = max(totals["max_turns"], state.turn_number)
        totals["turns"] += state.turn_number
        totals["score"] += player.get_victory_points()
        totals["opponent_score"] += opponent.get_victory_points()
        totals["tomb_points"] += player.vp_tokens
        totals["platinum_games"] += first_platinum is not None
        totals["platinum_first_turn"] += first_platinum or 0
        totals["mine_plays"] += sum(getattr(strategy, "mine_gains", Counter()).values())
        upgrades.update(getattr(strategy, "mine_gains", {}))
        multipliers.update(getattr(strategy, "multiplier_targets", {}))
    rate = statistics.mean(outcomes)
    pairs = [statistics.mean(outcomes[i : i + 2]) for i in range(0, games, 2)]
    se = statistics.stdev(pairs) / (len(pairs) ** 0.5) if len(pairs) > 1 else 0
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        rate=rate,
        paired_ci95=[max(0, rate - 1.96 * se), min(1, rate + 1.96 * se)],
        totals=dict(totals),
        mine_gains=dict(upgrades),
        multiplier_targets=dict(multipliers),
    )


def run(tasks, path, workers=6):
    start = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(match, tasks):
            results.append(r)
            if len(results) % 20 == 0:
                print(
                    f"{len(results)}/{len(tasks)} matchups, {time.time() - start:.1f}s",
                    flush=True,
                )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")
    if any(r["totals"]["truncated"] for r in results):
        raise RuntimeError("Truncated games require inspection")
    return results


REFERENCE = {"money": "Smithy"}
BASELINES = ["plain", "Smithy", "Laboratory", "Mine", "Priest", "Hoard", "Bank"]


def candidates():
    result = []
    for opening, second, mines, kings, multiplier in itertools.product(
        ["Mine", "Laboratory"],
        ["Priest", "Throne Room", "Mining Village", "Silver", "Market Square"],
        [1, 2, 3],
        [0, 1, 2],
        ["mine", "draw"],
    ):
        result.append(
            dict(opening=opening, second=second, mines=mines, kings=kings, multiplier=multiplier)
        )
    rng = random.Random(8811)
    for _ in range(160):
        result.append(
            dict(
                opening=rng.choice(["Mine", "Laboratory", "Priest"]),
                second=rng.choice(["Priest", "Throne Room", "Mining Village", "Silver", "Market Square"]),
                mines=rng.choice([1, 2, 3]),
                kings=rng.choice([0, 1, 2]),
                thrones=rng.choice([0, 1, 2]),
                labs=rng.choice([0, 1, 2, 3]),
                smithies=rng.choice([0, 1, 2]),
                villages=rng.choice([0, 1, 2]),
                priests=rng.choice([0, 1, 2]),
                squares=rng.choice([0, 1, 2, 3]),
                hoards=rng.choice([0, 0, 1]),
                banks=rng.choice([0, 0, 1]),
                golds=rng.choice([0, 1, 2]),
                silvers=rng.choice([0, 1, 2]),
                sewers=rng.choice([True, True, False]),
                upgrade=rng.choice(["climb", "copper", "silver"]),
                multiplier=rng.choice(["mine", "draw", "priest"]),
                terminal_order=rng.choice(["mine", "priest", "smithy"]),
                keep_coppers=rng.choice([0, 2, 3, 5]),
                green_turn=rng.choice([10, 12, 14, 16]),
                province_colonies=rng.choice([2, 4, 6]),
                kc_turn=rng.choice([1, 4, 7]),
            )
        )
    return result


def no_mine_candidates():
    """Engines that never buy Mine, to find the strongest alternative plan."""
    rng = random.Random(4411)
    result = []
    for _ in range(120):
        result.append(
            dict(
                mines=0,
                opening=rng.choice(["Laboratory", "Priest", "Silver", "Throne Room"]),
                second=rng.choice(["Priest", "Throne Room", "Mining Village", "Silver", "Market Square", "Smithy"]),
                kings=rng.choice([0, 1, 2]),
                thrones=rng.choice([0, 1, 2]),
                labs=rng.choice([0, 1, 2, 3, 4]),
                smithies=rng.choice([0, 1, 2]),
                villages=rng.choice([0, 1, 2]),
                priests=rng.choice([0, 1, 2]),
                squares=rng.choice([0, 1, 2, 3]),
                hoards=rng.choice([0, 1, 2]),
                banks=rng.choice([0, 1, 2]),
                golds=rng.choice([1, 2, 3, 4]),
                silvers=rng.choice([1, 2, 3]),
                sewers=rng.choice([True, False]),
                multiplier=rng.choice(["draw", "priest"]),
                terminal_order=rng.choice(["priest", "smithy"]),
                keep_coppers=rng.choice([0, 3, 5, 7]),
                green_turn=rng.choice([10, 12, 14, 16]),
                province_colonies=rng.choice([2, 4, 6]),
                kc_turn=rng.choice([1, 4, 7]),
            )
        )
    return result


def best_no_mine():
    results = json.loads(Path("docs/analysis/kimberley_nomine.json").read_text())
    rechecked = [r for r in results if r["games"] >= 400]
    return max(rechecked, key=lambda r: r["rate"])["a"]


def ablations(base):
    return {
        "no_mine": dict(base, mines=0, opening="Laboratory" if base.get("opening") == "Mine" else base.get("opening", "Laboratory")),
        "no_multipliers": dict(base, kings=0, thrones=0, second="Priest" if base.get("second") == "Throne Room" else base.get("second", "Priest")),
        "no_sewers": dict(base, sewers=False),
        "no_priest": dict(base, priests=0, second="Silver" if base.get("second") == "Priest" else base.get("second", "Silver")),
        "no_squares": dict(base, squares=0),
        "copper_first": dict(base, upgrade="copper"),
        "draw_multiplier": dict(base, multiplier="draw"),
    }


def confirmation_tasks(finalists):
    no_mine = best_no_mine()
    tasks = []
    for spec in finalists:
        tasks.append((spec, no_mine, 1000, 490000))
        for mode in BASELINES:
            tasks.append((spec, {"money": mode}, 1000, 500000))
    best = finalists[0]
    for name, spec in ablations(best).items():
        tasks.append((best, spec, 1000, 510000))
        tasks.append((spec, no_mine, 1000, 520000))
    tasks.append((no_mine, REFERENCE, 1000, 530000))
    return tasks


FINAL = dict(opening="Mine", second="Priest", mines=1, kings=0, thrones=0)


def final_tasks():
    """Confirm the published configuration, found by the multiplier ablation."""
    no_mine = best_no_mine()
    tasks = [(FINAL, no_mine, 1000, 540000)]
    tasks += [(FINAL, {"money": mode}, 1000, 550000) for mode in BASELINES]
    changes = dict(
        ablations(FINAL),
        throne_room=dict(FINAL, thrones=1),
        kings_court=dict(FINAL, kings=1),
        two_mines=dict(FINAL, mines=2),
        lab_opening=dict(FINAL, opening="Laboratory"),
        silver_second=dict(FINAL, second="Silver"),
    )
    changes.pop("no_multipliers")
    changes.pop("draw_multiplier")
    for spec in changes.values():
        tasks.append((FINAL, spec, 1000, 560000))
        tasks.append((spec, no_mine, 1000, 570000))
    return tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["smoke", "screen", "recheck", "nomine", "confirm", "final"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.stage == "smoke":
        print(json.dumps(match(({}, REFERENCE, 4, 1)), indent=2))
        return
    if args.stage == "screen":
        tasks = [(c, REFERENCE, 32, 200000) for c in candidates()]
    elif args.stage == "recheck":
        previous = json.loads(Path("docs/analysis/kimberley_screen.json").read_text())
        top = sorted(previous, key=lambda r: r["rate"], reverse=True)[:40]
        tasks = [(r["a"], REFERENCE, 400, 300000) for r in top]
    elif args.stage == "nomine":
        path = args.output or Path("docs/analysis/kimberley_nomine.json")
        screen = run([(c, REFERENCE, 32, 210000) for c in no_mine_candidates()], path, workers=args.workers)
        top = sorted(screen, key=lambda r: r["rate"], reverse=True)[:8]
        rechecked = run([(r["a"], REFERENCE, 400, 310000) for r in top], path, workers=args.workers)
        path.write_text(json.dumps(screen + rechecked, indent=2) + "\n")
        for r in sorted(rechecked, key=lambda r: r["rate"], reverse=True):
            print(round(r["rate"], 3), r["a"], flush=True)
        return
    elif args.stage == "final":
        tasks = final_tasks()
    else:
        previous = json.loads(Path("docs/analysis/kimberley_recheck.json").read_text())
        top = sorted(previous, key=lambda r: r["rate"], reverse=True)[:3]
        tasks = confirmation_tasks([r["a"] for r in top])
    path = args.output or Path(f"docs/analysis/kimberley_{args.stage}.json")
    results = run(tasks, path, workers=args.workers)
    for r in sorted(results, key=lambda r: r["rate"], reverse=True)[:15]:
        print(
            round(r["rate"], 3),
            r["a"],
            "vs",
            r["b"],
            "mine plays/game:",
            round(r["totals"]["mine_plays"] / r["games"], 1),
            flush=True,
        )


if __name__ == "__main__":
    main()
