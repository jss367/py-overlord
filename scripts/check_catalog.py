"""Check all committed catalog pages, including saved standings and card ranks."""

from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from catalog_pre_commit import catalog_files, render


def main() -> int:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
