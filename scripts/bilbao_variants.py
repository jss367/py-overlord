"""Hand local search around the Bilbao round-robin leader.

Generates one importable strategy file per variant under
``reports/bilbao/variants/`` and plays a round robin (or a champion-vs-all
sweep) with ``scripts/search_bilbao.py``. Run with ``PYTHONPATH=.``. The
sweep inputs behind the published guide live in ``scripts/bilbao_sweeps/``
(see its README for the exact command per sweep).
"""

import argparse
import json
from pathlib import Path

from scripts.search_bilbao import print_table, run

VARIANT_DIR = Path("reports/bilbao/variants")

TEMPLATE = '''"""Generated Bilbao variant: {name}."""
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategies.bilbao_seeds import {cls}


def create_variant() -> EnhancedStrategy:
    return {cls}(**{params!r})
'''


def write_variant(name: str, cls: str = "BilbaoAnvilFeodumVariant", **params) -> str:
    """Write one importable variant file; ``cls`` names the parametrised
    class in ``bilbao_seeds`` (a ``_class`` key in the sweep JSON overrides
    the ``--variant-class`` default per variant)."""
    VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    path = VARIANT_DIR / f"{name}.py"
    params = dict(params, name=name)
    path.write_text(TEMPLATE.format(name=name, cls=cls, params=params))
    return str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--sweep", required=True, help="JSON file: {name: params} variants.")
    parser.add_argument("--champion", help="Variant name to play against all others.")
    parser.add_argument("--extra", nargs="*", default=[], help="Loader names to add.")
    parser.add_argument("--output")
    parser.add_argument(
        "--variant-class",
        default="BilbaoAnvilFeodumVariant",
        help="Parametrised class in bilbao_seeds to instantiate (per-variant `_class` overrides).",
    )
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be at least 1")
    if args.games % 2:
        parser.error("--games must be even so each shuffle seed is played in both seats")
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    sweep = json.loads(Path(args.sweep).read_text())
    refs = [
        write_variant(name, cls=params.pop("_class", args.variant_class), **params)
        for name, params in sweep.items()
    ] + args.extra
    if args.champion:
        champ = str(VARIANT_DIR / f"{args.champion}.py")
        if args.champion not in sweep:
            champ = args.champion  # a loader name, e.g. "Bilbao Best Found"
            if champ not in refs:
                refs.append(champ)
        pairs = [(champ, r) for r in refs if r != champ]
        names = [champ] + [r for r in refs if r != champ]
    else:
        import itertools

        pairs = list(itertools.combinations(refs, 2))
        names = refs
    tasks = [(a, b, args.games, args.seed) for a, b in pairs]
    results = run(tasks, args.workers, args.output)
    print()
    print_table(names, results)


if __name__ == "__main__":
    main()
