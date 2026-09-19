"""Dedicated engine search against the frozen Collection–Swindler rush.

All screening, confirmation and validation stages use disjoint game seeds.
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
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.collection_imperial_envoy import (
    CollectionImperialEnvoy,
)
from dominion.strategy.strategies.village_envoy_engine import (
    VillageEnvoyEngine,
    SelectiveEnvoyEngine,
)
from scripts.search_collection_imperial_envoy import BOARD

RUSH = {
    "kind": "previous",
    "params": dict(collection=4, envoy=0, farm=1, green=12, swindler=2, village=2),
}
PREVIOUS_ENGINE = {
    "kind": "previous",
    "params": dict(
        collection=4, envoy=1, farm=1, ghost=2, green=12, swindler=2, village=2
    ),
}


def build(spec):
    cls = {
        "previous": CollectionImperialEnvoy,
        "engine": VillageEnvoyEngine,
        "hybrid": SelectiveEnvoyEngine,
    }[spec["kind"]]
    return cls(**spec["params"])


def canonical(spec):
    strategy = build(spec)
    return json.dumps(
        dict(
            kind=spec["kind"],
            params=getattr(
                strategy,
                "search_params",
                getattr(strategy, "engine_params", strategy.params),
            ),
        ),
        sort_keys=True,
    )


class AuditedAI(GeneticAI):
    def __init__(self, strategy):
        super().__init__(strategy)
        self.action_counts = Counter()
        self.empty_envoys = 0

    def choose_action(self, state, choices):
        choice = super().choose_action(state, choices)
        if choice is not None and getattr(state, "_choosing_main_action_phase", False):
            self.action_counts[choice.name] += 1
            if choice.name == "Imperial Envoy" and not (
                state.current_player.deck or state.current_player.discard
            ):
                self.empty_envoys += 1
        return choice


def match(task):
    a, b, games, seed = task
    wins = ties = truncated = 0
    scores = [0, 0]
    tokens = [0, 0]
    turns = 0
    decks = [Counter(), Counter()]
    actions = [Counter(), Counter()]
    empty_envoys = [0, 0]
    pairs = []
    kingdom = [get_card(n) for n in BOARD.kingdom_cards]
    for i in range(games):
        random.seed(seed + i // 2)
        ais = [AuditedAI(build(a)), AuditedAI(build(b))]
        if i % 2:
            ais.reverse()
        state = GameState(players=[], supply={})
        state.log_callback = lambda *_: None
        state.initialize_game(ais, kingdom)
        while not state.is_game_over() and state.turn_number < 160:
            state.play_turn()
        truncated += not state._normal_game_end_reached()
        players = state.players if not i % 2 else list(reversed(state.players))
        keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
        won = keys[0] > keys[1]
        tied = keys[0] == keys[1]
        wins += won
        ties += tied
        if not i % 2:
            pairs.append(0)
        pairs[-1] += (won + tied / 2) / 2
        turns += state.turn_number
        for j, p in enumerate(players):
            scores[j] += keys[j][0]
            tokens[j] += p.vp_tokens
            decks[j].update(c.name for c in p.all_cards())
            actions[j].update(p.ai.action_counts)
            empty_envoys[j] += p.ai.empty_envoys
    return dict(
        a=a,
        b=b,
        games=games,
        seed=seed,
        wins=wins,
        ties=ties,
        rate=(wins + ties / 2) / games,
        pair_scores=pairs,
        truncated=truncated,
        turns=turns / games,
        scores=[v / games for v in scores],
        tokens=[v / games for v in tokens],
        decks=[{k: round(v / games, 3) for k, v in sorted(d.items())} for d in decks],
        action_plays=[
            {k: round(v / games, 3) for k, v in sorted(d.items())} for d in actions
        ],
        empty_envoy_plays=[v / games for v in empty_envoys],
    )


def rank(rows, both=False):
    vals = {}
    specs = {}
    for r in rows:
        for side, score in (
            [("a", r["rate"]), ("b", 1 - r["rate"])] if both else [("a", r["rate"])]
        ):
            key = canonical(r[side])
            specs[key] = r[side]
            vals.setdefault(key, []).append(score)
    return sorted(
        [(sum(v) / len(v), specs[k]) for k, v in vals.items()], key=lambda x: -x[0]
    )


def candidates():
    plans = []
    for envoy, collection, order, farm_turn in itertools.product(
        (2, 3, 4, 5), (3, 5, 7), ("balanced", "income", "draw"), (8, 12, 99)
    ):
        plans.append(
            dict(
                envoy=envoy,
                village=envoy + 2,
                collection=collection,
                order=order,
                farm_turn=farm_turn,
            )
        )
    for seed in (319, 2718, 202609):
        rng = random.Random(seed)
        for _ in range(100):
            envoy = rng.choice([2, 3, 4, 5, 6])
            plans.append(
                dict(
                    envoy=envoy,
                    village=rng.choice([envoy, envoy + 2, 8]),
                    collection=rng.choice([2, 3, 4, 5, 6, 8]),
                    swindler=rng.choice([0, 1, 2]),
                    ghost=rng.choice([0, 0, 1, 2, 4]),
                    fish=rng.choice([0, 0, 1, 2]),
                    silver=rng.choice([0, 1, 2, 3]),
                    gold=rng.choice([0, 0, 1, 3]),
                    mystic=rng.choice([0, 0, 1, 3]),
                    ship=rng.choice([0, 0, 1, 2]),
                    opening=rng.choice(["Swindler", "Silver", "Village"]),
                    second=rng.choice(["Silver", "Swindler", "Village"]),
                    first_five=rng.choice(["Imperial Envoy", "Collection"]),
                    order=rng.choice(["balanced", "income", "draw", "income_heavy"]),
                    green=rng.choice([8, 12, 16, 99]),
                    farm_turn=rng.choice([0, 8, 12, 16, 99]),
                    farm_collections=rng.choice([1, 2, 3]),
                    cheap_first=rng.choice([False, True]),
                    spare_actions=rng.choice([0, 1, 2]),
                    min_draw=rng.choice([1, 2, 3, 5]),
                    attack_first=rng.choice([False, True]),
                    adaptive_draw=rng.choice([False, True]),
                )
            )
    return [dict(kind="engine", params=p) for p in plans]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=["screen", "hybrid", "refine", "confirm", "validate"]
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--extra", type=Path, help="Additional screened results for confirmation"
    )
    parser.add_argument("--games", type=int, default=40)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.games <= 0 or args.games % 2:
        parser.error("games must be positive and even")
    if args.mode not in {"screen", "hybrid"} and not args.input:
        parser.error("--input required")
    if args.mode == "screen":
        tasks = [
            (p, RUSH, args.games, 30000000 + 10000 * i)
            for i, p in enumerate(candidates())
        ]
    elif args.mode == "hybrid":
        plans = [
            dict(
                kind="hybrid",
                params=dict(
                    collection=collection,
                    envoy=envoy,
                    village=village,
                    ghost=ghost,
                    swindler=2,
                    green=green,
                    farm=1,
                ),
            )
            for collection, envoy, village, ghost, green in itertools.product(
                (4, 6), (1, 2, 3, 4), (3, 6), (0, 2), (8, 12, 99)
            )
        ]
        tasks = [
            (p, RUSH, args.games, 35000000 + 10000 * i) for i, p in enumerate(plans)
        ]
    else:
        input_rows = json.loads(args.input.read_text())
        if args.extra:
            input_rows += json.loads(args.extra.read_text())
        ranked = rank(input_rows)
        if args.mode == "refine":
            plans = [p for _, p in ranked[:12]]
            values = dict(
                envoy=[1, 2, 3, 4, 5, 6],
                village=[2, 4, 6, 8],
                collection=[2, 4, 6, 8],
                swindler=[0, 1, 2],
                ghost=[0, 2, 4],
                min_draw=[1, 2, 3, 5],
                farm_turn=[0, 8, 12, 99],
                farm_collections=[1, 2, 3],
                green=[0, 8, 12, 99],
                cheap_first=[False, True],
                order=["balanced", "income", "draw", "income_heavy"],
                silver=[0, 1, 2, 3],
                second=["Silver", "Swindler", "Village"],
                first_five=["Imperial Envoy", "Collection"],
            )
            for _, parent in ranked[:6]:
                for key, options in values.items():
                    plans.extend(
                        dict(kind="engine", params=dict(parent["params"], **{key: v}))
                        for v in options
                    )
            # Include full draw engines whose income is Gold or Mystic,
            # rather than requiring Collection as the scoring payload.
            for envoy, gold, mystic, green in itertools.product(
                (2, 3, 4), (3, 6), (0, 4), (8, 12, 99)
            ):
                plans.append(
                    dict(
                        kind="engine",
                        params=dict(
                            envoy=envoy,
                            village=envoy + 2,
                            collection=0,
                            gold=gold,
                            gold_core=True,
                            mystic=mystic,
                            green=green,
                            farm_turn=99,
                            first_five="Imperial Envoy",
                        ),
                    )
                )
            unique = {canonical(p): p for p in plans}
            panel = [RUSH, ranked[0][1]]
            tasks = [
                (p, b, args.games, 40000000 + 20000 * i + 5000 * j)
                for i, p in enumerate(unique.values())
                for j, b in enumerate(panel)
            ]
        elif args.mode == "confirm":
            direct = rank([r for r in input_rows if r["b"] == RUSH])
            deep = [
                (score, p) for score, p in direct if p["params"].get("envoy", 3) >= 2
            ]
            finalists = {canonical(p): p for _, p in ranked[:8] + direct[:8] + deep[:4]}
            tasks = [
                (p, b, args.games, 50000000 + 20000 * i + 5000 * j)
                for i, p in enumerate(finalists.values())
                for j, b in enumerate([RUSH, PREVIOUS_ENGINE, ranked[0][1]])
            ]
        else:
            # The user's comparison target is the frozen rush. Choose by
            # confirmed performance against it, not by easy-panel averages.
            direct = rank([r for r in input_rows if r["b"] == RUSH])
            winner = direct[0][1]
            deep = next(p for _, p in direct if p["params"].get("envoy", 3) >= 2)
            opponents = [RUSH, PREVIOUS_ENGINE] + [p for _, p in direct[1:4]]
            tasks = [
                (winner, b, args.games, 60000000 + 10000 * i)
                for i, b in enumerate(opponents)
            ]
            if canonical(deep) != canonical(winner):
                tasks.append((deep, RUSH, args.games, 61000000))
            # Isolate the effect of avoiding debt for empty or nearly empty draws.
            wasteful = dict(
                kind=winner["kind"], params=dict(winner["params"], min_draw=0)
            )
            tasks.append((winner, wasteful, args.games, 62000000))
    start = time.monotonic()
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(match, tasks):
            rows.append(r)
            if len(rows) % 25 == 0:
                print(
                    f"{len(rows)}/{len(tasks)} matches in {time.monotonic() - start:.1f}s",
                    flush=True,
                )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2) + "\n")
    for score, p in rank(rows)[:12]:
        print(round(score, 4), json.dumps(p, sort_keys=True), flush=True)
    print(
        "Games",
        sum(r["games"] for r in rows),
        "truncated",
        sum(r["truncated"] for r in rows),
        flush=True,
    )


if __name__ == "__main__":
    main()
