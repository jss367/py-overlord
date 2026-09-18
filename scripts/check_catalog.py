"""Check all committed catalog pages, including saved standings and card ranks."""

import argparse
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

from catalog_pre_commit import catalog_files, render

# Keep the documented direct invocation working without an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dominion.reporting.strategy_pages import collect_rendered_strategies, missing_decision_descriptions


def check_decision_descriptions(items) -> bool:
    """Report explanation gaps without disguising them as unconditional rules."""
    missing = [
        (item.display_name, missing_decision_descriptions(item.strategy))
        for item in items
    ]
    missing = [(name, hooks) for name, hooks in missing if hooks]
    if missing:
        print(f"Warning: {len(missing)} strategies have custom behaviors without readable instructions:")
        for name, hooks in missing:
            print(f"  {name}: {', '.join(hooks)}")
    return not missing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-descriptions", action="store_true",
        help="Fail if a custom behavior has neither readable instructions nor a docstring.",
    )
    args = parser.parse_args(argv)
    descriptions_complete = check_decision_descriptions(collect_rendered_strategies())
    root = Path.cwd()
    with TemporaryDirectory(prefix="dominion-catalog-check-") as directory:
        scratch = Path(directory)
        output = scratch / "reports"
        leaderboard = root / "reports/strategies/leaderboard.html"
        if leaderboard.exists():
            destination = output / "strategies/leaderboard.html"
            destination.parent.mkdir(parents=True)
            shutil.copyfile(leaderboard, destination)
        render(root, output)
        actual = catalog_files(root)
        expected = catalog_files(scratch)
        stale = sorted(path for path in actual.keys() | expected.keys() if actual.get(path) != expected.get(path))
        if stale:
            print("Catalog is stale. Run: PYTHONPATH=. python scripts/render_catalog.py")
            for path in stale:
                print(f"  {path}")
            return 1
    print("Catalog is current, including saved tournament results.")
    if args.strict_descriptions and not descriptions_complete:
        print("Catalog descriptions are incomplete; strict validation failed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
