"""Re-base exported island champions onto their hand-written seed class.

Champions exported before ``save_strategy_as_python`` learned to keep a seed
subclass as the base lose the seed's coded decision hooks (King's Court
targets, Steward mode, Masquerade pass, pile-out). This rewrites such files
so the champion class inherits from the seed class named by the island, and
restores the seed's ``multiplier_priority``. Files that already inherit
from a seed base are copied unchanged.

    PYTHONPATH=. python scripts/graft_seed_hooks.py \
        generated_strategies/island_champions/albuquerque/<RUN_ID> --out <DIR>
"""

import argparse
import re
from pathlib import Path

from dominion.strategy.strategy_loader import StrategyLoader


def graft(path: Path, out_dir: Path, loader: StrategyLoader) -> str:
    text = path.read_text()
    if "_SeedBase" in text:
        (out_dir / path.name).write_text(text)
        return "kept"
    island = path.stem.removesuffix("_champion").replace("_", " ").title()
    seed = loader.get_strategy(island)
    if seed is None:
        return f"no seed named {island!r}"
    cls = type(seed)
    if cls.__name__ in {"EnhancedStrategy", "BaseStrategy"}:
        (out_dir / path.name).write_text(text)
        return "plain seed"
    text = text.replace(
        "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule",
        "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule\n"
        f"from {cls.__module__} import {cls.__name__} as _SeedBase",
        1,
    )
    text = re.sub(r"^class (\w+)\(EnhancedStrategy\):", r"class \1(_SeedBase):", text, count=1, flags=re.M)
    multiplier = getattr(seed, "multiplier_priority", None) or []
    if multiplier:
        lines = ["        self.multiplier_priority = ["]
        for rule in multiplier:
            src = getattr(rule.condition, "_source", None) if rule.condition else None
            lines.append(f"            PriorityRule({rule.card_name!r}, {src})," if src else f"            PriorityRule({rule.card_name!r}),")
        lines.append("        ]")
        text = text.replace("\ndef create_", "\n" + "\n".join(lines) + "\n\n\ndef create_", 1)
    (out_dir / path.name).write_text(text)
    return f"grafted onto {cls.__name__}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    loader = StrategyLoader()
    for path in sorted(args.run_dir.glob("*_champion.py")):
        print(f"{path.name}: {graft(path, args.out, loader)}")


if __name__ == "__main__":
    main()
