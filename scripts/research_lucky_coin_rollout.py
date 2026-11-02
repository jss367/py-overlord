"""Save real decisions, audit alternatives, and test shared rollout players."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import random
from statistics import NormalDist
import time

import cloudpickle

from dominion.ai.lucky_coin_rollout import MODEL_VERSION, RolloutController
from scripts.search_lucky_coin_ruins import setup

KINDS = (
    "action",
    "treasure",
    "buy",
    "trash",
    "free_gain",
    "emperor",
    "effect",
    "spice_trash",
    "spice_mode",
)


def policies():
    frozen = json.loads(
        Path("scripts/data/lucky_coin_ruins/rollout-policy-specs.json").read_text()
    )
    return frozen["tea"], frozen["shrine"]


def play(
    seed,
    swap=False,
    enabled=(False, False),
    *,
    samples=2,
    refine=4,
    observer=None,
    matchup="cross",
    live_verify=16,
    decision_budget=2,
    search_kinds=None,
    legacy_change_pass=False,
    schedule="legacy",
    adaptive_refine=None,
):
    a, b = policies()
    if matchup == "tea-mirror":
        b = a
    elif matchup == "shrine-mirror":
        a = b
    s = setup(a, b, seed, swap)
    flags = tuple(reversed(enabled)) if swap else enabled
    c = RolloutController(
        samples=samples,
        refine=refine,
        verify=live_verify,
        enabled=flags,
        observer=observer,
        decisions_per_turn=decision_budget,
        search_kinds=search_kinds,
        allow_legacy_change_pass=legacy_change_pass,
        schedule=schedule,
        adaptive_refine=adaptive_refine,
    )
    c.install(s)
    while not s.is_game_over() and s.turn_number < 160:
        c.begin(s, dict(seed=seed, swap=swap))
        s.play_turn()
    if not s._normal_game_end_reached():
        raise RuntimeError("Real game reached the turn cap")
    ps = list(reversed(s.players)) if swap else s.players
    keys = [(p.get_victory_points(), -p.turns_taken) for p in ps]
    score = 1 if keys[0] > keys[1] else 0.5 if keys[0] == keys[1] else 0
    return dict(
        seed=seed,
        swap=swap,
        score=score,
        scores=[k[0] for k in keys],
        planned_decisions=len(c.records),
        rollouts=c.rollouts,
        changed=sum(x["choice"] != x["baseline"] for x in c.records),
        search_counts=dict(Counter(d["kind"] for d in c.records)),
        changed_counts=dict(
            Counter(d["kind"] for d in c.records if d["choice"] != d["baseline"])
        ),
        decisions=c.records,
        decks=[dict(Counter(x.name for x in p.all_cards())) for p in ps],
    )


def collect(args):
    kinds = args.collect_kinds or KINDS
    reservoir = {kind: [] for kind in kinds}
    seen = Counter()
    rng = random.Random(317)

    def observer(d):
        if d.kind not in reservoir:
            return
        seen[d.kind] += 1
        index = rng.randrange(seen[d.kind])
        if len(reservoir[d.kind]) < args.per_kind:
            reservoir[d.kind].append(d)
        elif index < args.per_kind:
            reservoir[d.kind][index] = d

    start = time.time()
    for i in range(args.games):
        play(args.seed + i // 2, bool(i % 2), observer=observer)
    positions = [d for kind in kinds for d in reservoir[kind]]
    if len(positions) != args.per_kind * len(kinds):
        raise RuntimeError(
            f"Insufficient positions: { {k: len(v) for k, v in reservoir.items()} }"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(cloudpickle.dumps(positions))
    meta = dict(
        model_version=MODEL_VERSION,
        seed=args.seed,
        games=args.games,
        positions=len(positions),
        seen=dict(seen),
        by_kind={k: len(v) for k, v in reservoir.items()},
        elapsed=time.time() - start,
        observations=[
            dict(
                identifier=d.identifier,
                kind=d.kind,
                baseline=d.baseline,
                options=d.options,
                option_labels=d.option_labels,
                observation=d.observation,
            )
            for d in positions
        ],
    )
    args.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print({k: v for k, v in meta.items() if k != "observations"}, flush=True)


_AUDIT = []


def init_audit(path):
    global _AUDIT
    _AUDIT = cloudpickle.loads(Path(path).read_bytes())


def audit_one(task):
    index, samples, verify, adaptive = task
    d = _AUDIT[index]
    c = RolloutController(enabled=(False, False))
    result = c.evaluate(d, samples, adaptive=adaptive)
    diffs = []
    base = []
    alternative = []
    if result["choice"] != d.baseline:
        for j in range(verify):
            seed = c.sample_seed(d, j, salt=1)
            a = c.outcome(d, d.baseline, seed)
            b = c.outcome(d, result["choice"], seed)
            base.append(a)
            alternative.append(b)
            diffs.append(b - a)
    else:
        diffs = [0.0] * verify
    mean = sum(diffs) / len(diffs)
    se = (sum((x - mean) ** 2 for x in diffs) / (len(diffs) - 1) / len(diffs)) ** 0.5
    result.update(
        index=index,
        verified_delta=mean,
        verified_ci95=[mean - 1.96 * se, mean + 1.96 * se],
        verification_samples=verify,
        baseline_verification=base,
        alternative_verification=alternative,
        rollouts=c.rollouts,
    )
    return result


def audit(args):
    positions = cloudpickle.loads(args.positions.read_bytes())
    tasks = [
        (i, args.samples, args.verify, args.adaptive_refine)
        for i in range(len(positions))
    ]
    results = []
    start = time.time()
    with ProcessPoolExecutor(
        max_workers=args.workers,
        initializer=init_audit,
        initargs=(str(args.positions),),
    ) as pool:
        for r in pool.map(audit_one, tasks):
            results.append(r)
            if len(results) % 8 == 0:
                print(
                    f"{len(results)}/{len(tasks)} positions, {time.time() - start:.1f}s",
                    flush=True,
                )
    out = dict(
        positions=len(results),
        adaptive_refine=args.adaptive_refine,
        samples=args.samples,
        verify=args.verify,
        changed=sum(x["choice"] != x["baseline"] for x in results),
        positive_verified=sum(x["verified_ci95"][0] > 0 for x in results),
        negative_verified=sum(x["verified_ci95"][1] < 0 for x in results),
        mean_verified_delta=sum(x["verified_delta"] for x in results) / len(results),
        rollouts=sum(x["rollouts"] for x in results),
        results=results,
    )
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    print({k: v for k, v in out.items() if k != "results"}, flush=True)


def confirm_one(task):
    index, choice, samples, z = task
    d = _AUDIT[index]
    c = RolloutController(enabled=(False, False))
    diffs = []
    baseline = []
    alternative = []
    for j in range(samples):
        seed = c.sample_seed(d, j, salt=2)
        a = c.outcome(d, d.baseline, seed)
        b = c.outcome(d, choice, seed)
        baseline.append(a)
        alternative.append(b)
        diffs.append(b - a)
    mean = sum(diffs) / len(diffs)
    se = (sum((x - mean) ** 2 for x in diffs) / (len(diffs) - 1) / len(diffs)) ** 0.5
    return dict(
        index=index,
        identifier=d.identifier,
        kind=d.kind,
        observation=d.observation,
        baseline=d.baseline,
        choice=choice,
        samples=samples,
        delta=mean,
        adjusted_ci95=[mean - z * se, mean + z * se],
        baseline_win_share=sum(baseline) / samples,
        alternative_win_share=sum(alternative) / samples,
        rollouts=c.rollouts,
    )


def confirm(args):
    audit_result = json.loads(args.audit.read_text())
    selected = [r for r in audit_result["results"] if r["verified_ci95"][0] > 0]
    if not selected:
        raise RuntimeError("No positive audit positions to confirm")
    z = NormalDist().inv_cdf(1 - 0.05 / (2 * len(selected)))
    tasks = [(r["index"], r["choice"], args.verify, z) for r in selected]
    with ProcessPoolExecutor(
        max_workers=min(args.workers, len(tasks)),
        initializer=init_audit,
        initargs=(str(args.positions),),
    ) as pool:
        results = list(pool.map(confirm_one, tasks))
    out = dict(
        familywise_alpha=0.05,
        adjustment="Bonferroni over independently confirmed positions",
        z=z,
        independent_sample_salt=2,
        results=results,
        rollouts=sum(r["rollouts"] for r in results),
    )
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    for r in results:
        print(
            r["kind"],
            r["baseline"],
            r["choice"],
            r["delta"],
            r["adjusted_ci95"],
            flush=True,
        )


def game_task(task):
    (
        seed,
        swap,
        enabled,
        samples,
        refine,
        matchup,
        live_verify,
        decision_budget,
        search_kinds,
        legacy_change_pass,
        schedule,
        adaptive_refine,
    ) = task
    start = time.time()
    r = play(
        seed,
        swap,
        enabled,
        samples=samples,
        refine=refine,
        matchup=matchup,
        live_verify=live_verify,
        decision_budget=decision_budget,
        search_kinds=search_kinds,
        legacy_change_pass=legacy_change_pass,
        schedule=schedule,
        adaptive_refine=adaptive_refine,
    )
    r["changed_decisions"] = [
        d for d in r.pop("decisions") if d["choice"] != d["baseline"]
    ]
    r["seconds"] = time.time() - start
    return r


def evaluate(args):
    enabled = {
        "both": (True, True),
        "tea": (True, False),
        "shrine": (False, True),
        "first": (True, False),
        "second": (False, True),
        "neither": (False, False),
    }[args.planned]
    tasks = [
        (
            args.seed + i // 2,
            bool(i % 2),
            enabled,
            args.samples,
            args.refine,
            args.matchup,
            args.live_verify,
            args.decision_budget,
            args.search_kinds,
            args.legacy_change_pass,
            args.schedule,
            args.adaptive_refine,
        )
        for i in range(args.games)
    ]
    results = []
    start = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(game_task, tasks):
            results.append(r)
            if len(results) % 4 == 0:
                print(
                    f"{len(results)}/{len(tasks)} games, {time.time() - start:.1f}s",
                    flush=True,
                )
    vals = [r["score"] for r in results]
    pairs = [sum(vals[i : i + 2]) / 2 for i in range(0, len(vals), 2)]
    rate = sum(vals) / len(vals)
    se = (
        (sum((x - rate) ** 2 for x in pairs) / (len(pairs) - 1) / len(pairs)) ** 0.5
        if len(pairs) > 1
        else 0
    )
    out = dict(
        seed=args.seed,
        games=args.games,
        planned=args.planned,
        live_verify=args.live_verify,
        legacy_change_pass=args.legacy_change_pass,
        schedule=args.schedule,
        adaptive_refine=args.adaptive_refine,
        decision_budget=args.decision_budget,
        search_kinds=args.search_kinds,
        samples=args.samples,
        refine=args.refine,
        matchup=args.matchup,
        first_policy_win_share=rate,
        ci95=[max(0, rate - 1.96 * se), min(1, rate + 1.96 * se)],
        rollouts=sum(r["rollouts"] for r in results),
        results=results,
    )
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    print({k: v for k, v in out.items() if k != "results"}, flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["collect", "audit", "confirm", "evaluate"])
    p.add_argument("--games", type=int, default=32)
    p.add_argument("--seed", type=int, default=10000000)
    p.add_argument("--per-kind", type=int, default=8)
    p.add_argument("--positions", type=Path)
    p.add_argument("--audit", type=Path)
    p.add_argument(
        "--matchup", choices=["cross", "tea-mirror", "shrine-mirror"], default="cross"
    )
    p.add_argument("--samples", type=int, default=2)
    p.add_argument("--refine", type=int, default=4)
    p.add_argument(
        "--schedule",
        choices=["legacy", "cleanup"],
        default="legacy",
        help="Cleanup uses separate named quotas instead of --decision-budget",
    )
    p.add_argument(
        "--adaptive-refine",
        type=int,
        help="Extra discovery worlds for baseline and leaders; replaces --refine",
    )
    p.add_argument(
        "--collect-kinds",
        help="Comma-separated categories for the saved-position audit",
    )
    p.add_argument("--live-verify", type=int, default=16)
    p.add_argument(
        "--legacy-change-pass",
        action="store_true",
        help="Reproduce the pre-fix research model only",
    )
    p.add_argument("--decision-budget", type=int, default=2)
    p.add_argument(
        "--search-kinds", help="Comma-separated decision categories; default all"
    )
    p.add_argument("--verify", type=int, default=32)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument(
        "--planned",
        choices=["both", "tea", "shrine", "first", "second", "neither"],
        default="both",
    )
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.search_kinds = args.search_kinds.split(",") if args.search_kinds else None
    args.collect_kinds = args.collect_kinds.split(",") if args.collect_kinds else None
    if args.collect_kinds and not set(args.collect_kinds) <= set(KINDS):
        p.error("Unknown collection category")
    if args.search_kinds and not set(args.search_kinds) <= set(KINDS + ("gain",)):
        p.error("Unknown search category")
    if (
        args.games < 2
        or args.games % 2
        or args.samples < 1
        or args.verify < 2
        or args.live_verify < 0
        or args.refine < 0
        or args.workers < 1
        or args.decision_budget < 2
        or (args.adaptive_refine is not None and args.adaptive_refine < 0)
    ):
        p.error("Require an even positive game count, positive samples and verify >= 2")
    if args.mode in ("audit", "confirm") and args.positions is None:
        p.error("--positions is required for this mode")
    if args.mode == "confirm" and args.audit is None:
        p.error("--audit is required for confirmation")
    if args.mode == "collect":
        collect(args)
    elif args.mode == "audit":
        audit(args)
    elif args.mode == "confirm":
        confirm(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
