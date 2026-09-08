"""Focused Mine/Guildhall search with paired seats and actual combo-use auditing."""

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
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.projects.registry import get_project
from dominion.prophecies.registry import get_prophecy
from generated_strategies.mine_guildhall import MineGuildhall, SETUPS
from generated_strategies.tea_house_kind_emperor import TeaHouseEmperor
from scripts.search_tea_house_kind_emperor import BOARD, CHAMPION


class AuditedState(GameState):
    def gain_card(self, player, card, *args, **kwargs):
        before = player.coin_tokens
        result = super().gain_card(player, card, *args, **kwargs)
        if hasattr(self, "coffers_generated"):
            self.coffers_generated[self.players.index(player)] += max(
                0, player.coin_tokens - before
            )
        return result


def make(spec):
    return (
        TeaHouseEmperor(**spec["reference"])
        if "reference" in spec
        else MineGuildhall(**spec)
    )


def match(task):
    a, b, games, seed = task
    outcomes = []
    totals = Counter()
    upgrades = Counter()
    triples = Counter()
    for i in range(games):
        random.seed(seed + i // 2)
        strategy = make(a)
        ais = [GeneticAI(strategy), GeneticAI(make(b))]
        if i % 2:
            ais.reverse()
        state = AuditedState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(
            ais,
            [get_card(n) for n in BOARD.kingdom_cards],
            projects=[get_project("Guildhall")],
            prophecy=get_prophecy("Kind Emperor"),
        )
        player = state.players[i % 2]
        opponent = state.players[1 - i % 2]
        first_mine = first_guild = first_both = None
        state.coffers_generated = [0, 0]
        while not state.is_game_over() and state.turn_number < 160:
            active = state.current_player
            state.play_turn()
            if active is player:
                has_mine = player.count("Mine") > 0
                has_guild = any(p.name == "Guildhall" for p in player.projects)
                if has_mine and first_mine is None:
                    first_mine = player.turns_taken
                if has_guild and first_guild is None:
                    first_guild = player.turns_taken
                if has_mine and has_guild and first_both is None:
                    first_both = player.turns_taken
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
        totals["coffers_generated"] += state.coffers_generated[i % 2]
        for name, value in [
            ("mine", first_mine),
            ("guildhall", first_guild),
            ("both", first_both),
        ]:
            totals[f"{name}_games"] += value is not None
            totals[f"{name}_first_turn"] += value or 0
        upgrades.update(getattr(strategy, "mine_gains", {}))
        triples.update(getattr(strategy, "mastermind_targets", {}))
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
        mastermind_targets=dict(triples),
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


def candidates():
    result = []
    for setup, opening, mines, envoys, masterminds in itertools.product(
        list(SETUPS)[:8], ["Fortune Hunter", "Courier"], [1, 2, 3], [1, 2], [0, 1, 2]
    ):
        result.append(
            dict(
                setup=setup,
                opening=opening,
                mines=mines,
                envoys=envoys,
                masterminds=masterminds,
                free="mine_first" if "free_mine" in setup else "adaptive",
            )
        )
    rng = random.Random(8811)
    for _ in range(160):
        result.append(
            dict(
                setup=rng.choice(list(SETUPS)[:8]),
                opening=rng.choice(["Fortune Hunter", "Courier", "Silver"]),
                mines=rng.choice([1, 2, 3]),
                envoys=rng.choice([0, 1, 2]),
                masterminds=rng.choice([0, 1, 2]),
                free=rng.choice(
                    ["adaptive", "mine_first", "draw_first", "mastermind_first"]
                ),
                upgrade=rng.choice(["copper", "silver", "buried", "gold"]),
                triple=rng.choice(["mine", "tea", "draw"]),
                green_turn=rng.choice([4, 6, 8, 10]),
                buried=rng.choice([0, 1, 2]),
                mine_order=rng.choice(["early", "late"]),
            )
        )
    return result


def refinement_candidates():
    result = []
    for setup, upgrade, envoys, green, order in itertools.product(
        ["two_tea_mine_guild", "tea_mine_guild", "mine_guild_tea"],
        ["copper", "silver", "gold"],
        [1, 2],
        [3, 6, 9],
        ["early", "late"],
    ):
        result.append(
            dict(
                setup=setup,
                upgrade=upgrade,
                envoys=envoys,
                green_turn=green,
                mine_order=order,
            )
        )
    for setup, upgrade, masterminds, teas in itertools.product(
        ["mine_mastermind_guild", "mine_guild"],
        ["copper", "silver", "gold"],
        [0, 1, 2],
        [0, 2, 4],
    ):
        result.append(
            dict(
                setup=setup,
                upgrade=upgrade,
                masterminds=masterminds,
                teas=teas,
                envoys=2,
            )
        )
    for setup, free, silvers, buried in itertools.product(
        ["two_tea_mine_guild", "free_mine"],
        ["mine_first", "draw_first"],
        [0, 1, 3],
        [0, 2],
    ):
        result.append(
            dict(
                setup=setup,
                free=free,
                silvers=silvers,
                buried=buried,
                envoys=2,
                upgrade="buried" if buried else "silver",
            )
        )
    return result


CONFIRMATION_CANDIDATES = [
    dict(
        setup="tea_mine_guild",
        upgrade="silver",
        envoys=2,
        green_turn=6,
        mine_order="early",
    ),
    dict(
        setup="two_tea_mine_guild",
        free="mine_first",
        silvers=3,
        buried=0,
        envoys=2,
        upgrade="silver",
    ),
    dict(
        setup="two_tea_mine_guild",
        upgrade="copper",
        envoys=2,
        green_turn=9,
        mine_order="early",
    ),
    dict(
        setup="mine_mastermind_guild", upgrade="silver", masterminds=1, teas=4, envoys=2
    ),
    dict(setup="mine_guild", upgrade="copper", masterminds=1, teas=2, envoys=2),
]


def confirmation_tasks():
    reference = {"reference": CHAMPION}
    combo = CONFIRMATION_CANDIDATES[0]
    without_guild = dict(combo, guildhall=False)
    without_mine = dict(combo, mines=0)
    neither = dict(combo, mines=0, guildhall=False)
    candidates = CONFIRMATION_CANDIDATES + [without_guild, without_mine, neither]
    return [(c, reference, 2000, 500000) for c in candidates] + [
        (combo, without_guild, 2000, 510000),
        (combo, neither, 2000, 520000),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage", choices=["screen", "recheck", "refine", "confirm", "upgrades", "smoke"]
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reference = {"reference": CHAMPION}
    if args.stage == "smoke":
        print(json.dumps(match(({}, reference, 4, 1)), indent=2))
        return
    if args.stage == "screen":
        tasks = [(c, reference, 32, 200000) for c in candidates()]
    elif args.stage == "refine":
        tasks = [(c, reference, 96, 400000) for c in refinement_candidates()]
    elif args.stage == "confirm":
        tasks = confirmation_tasks()
    elif args.stage == "upgrades":
        base = CONFIRMATION_CANDIDATES[0]
        tasks = [
            (dict(base, **change), reference, 2000, 500000)
            for change in [dict(upgrade="copper"), dict(mine_order="late")]
        ]
    else:
        previous = json.loads(
            Path("docs/analysis/mine_guildhall_screen.json").read_text()
        )
        top = sorted(previous, key=lambda r: r["rate"], reverse=True)[:24]
        tasks = [(r["a"], reference, 400, 300000) for r in top]
    path = args.output or Path(f"docs/analysis/mine_guildhall_{args.stage}.json")
    results = run(tasks, path)
    for r in sorted(results, key=lambda r: r["rate"], reverse=True)[:15]:
        print(
            r["rate"],
            r["a"],
            "both:",
            r["totals"]["both_games"] / r["games"],
            flush=True,
        )


if __name__ == "__main__":
    main()
