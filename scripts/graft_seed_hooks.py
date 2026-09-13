"""Re-base exported island champions onto their hand-written seed class.

Champions exported before ``save_strategy_as_python`` learned to keep a seed
subclass as the base lose the seed's coded decision hooks (King's Court
targets, Steward mode, Masquerade pass, pile-out). This rewrites such files
so the champion class inherits from the seed class named by the island, and
restores the seed's ``multiplier_priority``. Files that already inherit
from a seed base are copied unchanged.

The old exporter omitted any priority list that was empty, and the seed's
``__init__`` would silently refill such a list with the seed's defaults once
the class is re-based. Every standard list absent from the old file is
therefore written out as ``[]`` so the grafted champion still describes the
strategy that was actually evaluated.

``multiplier_priority`` is the one list deliberately taken from the seed: the
genetic trainer never mutates it, so the seed's list is exactly what the
champion used during evaluation, and the old exporter simply never wrote it.

    PYTHONPATH=. python scripts/graft_seed_hooks.py \
        generated_strategies/island_champions/albuquerque/<RUN_ID> --out <DIR>
"""

import argparse
import re
from pathlib import Path

from dominion.strategy.strategy_loader import StrategyLoader

# Lists the old exporter dropped when empty and a seed ``__init__`` may fill.
STANDARD_LISTS = (
    "gain_priority",
    "action_priority",
    "treasure_priority",
    "trash_priority",
    "bounty_hunter_exile_priority",
    "way_policy",
)


def _missing_lists(text: str) -> list[str]:
    """Standard lists the old export never assigns (i.e. were empty)."""
    return [
        name
        for name in STANDARD_LISTS
        if re.search(rf"^\s+self\.{name}\s*=", text, flags=re.M) is None
    ]


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
    # Match the whole import line so a trailing ``, WayRule`` (or any other
    # name) stays on the original import instead of the seed import.
    text, n = re.subn(
        r"^(from dominion\.strategy\.enhanced_strategy import .*)$",
        rf"\1\nfrom {cls.__module__} import {cls.__name__} as _SeedBase",
        text,
        count=1,
        flags=re.M,
    )
    if n == 0:
        return "no enhanced_strategy import to graft onto"
    text = re.sub(r"^class (\w+)\(EnhancedStrategy\):", r"class \1(_SeedBase):", text, count=1, flags=re.M)
    # Re-basing runs the seed's __init__, which fills every list the old
    # export left out because it was empty; pin those back to [] right after
    # super().__init__() so the champion keeps its evolved (empty) lists.
    missing = _missing_lists(text)
    if missing:
        def _pin(match: re.Match) -> str:
            indent = match.group(1)
            return match.group(0) + "".join(f"{indent}self.{name} = []\n" for name in missing)

        text, n = re.subn(r"^(\s+)super\(\)\.__init__\(\)\n", _pin, text, count=1, flags=re.M)
        if n == 0:
            return "no super().__init__() call to pin empty lists after"
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
