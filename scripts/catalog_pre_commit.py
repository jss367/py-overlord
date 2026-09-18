"""Refresh the catalog from Git's index without staging files or touching source edits."""

import os
from pathlib import Path
import shlex
import subprocess
import sys
from tempfile import TemporaryDirectory


CATALOG_DIRS = ("reports/boards", "reports/strategies")


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def relevant(path: str) -> bool:
    return path.startswith(("dominion/", "boards/", "generated_strategies/", "reports/")) or path in {
        "compare_all_strategies.py", "requirements.txt", "pyproject.toml",
        "scripts/render_catalog.py", "scripts/catalog_pre_commit.py",
    }


def catalog_files(root: Path) -> dict[str, bytes]:
    paths = [root / "reports/index.html"]
    for directory in CATALOG_DIRS:
        paths.extend((root / directory).rglob("*.html"))
    if any(path.is_symlink() for path in paths):
        raise ValueError("Catalog files must not be symlinks.")
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in paths if path.is_file()}


def render(root: Path, output: Path | None = None) -> None:
    # Prevent a parent environment from importing unstaged modules or sending
    # subprocess Git commands to the original checkout.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["PYTHONPATH"] = str(root)
    command = [sys.executable, str(root / "scripts/render_catalog.py")]
    if output is not None:
        command.extend(["--output-dir", str(output)])
    subprocess.run(command, cwd=root, env=env, check=True)


def refresh_staged_catalog(root: Path) -> int:
    staged = git(root, "diff", "--cached", "--name-only", "--no-renames", "-z").decode().split("\0")
    if not any(relevant(path) for path in staged):
        return 0
    with TemporaryDirectory(prefix="dominion-staged-catalog-") as directory:
        snapshot = Path(directory)
        git(root, "checkout-index", "--all", f"--prefix={snapshot}/")
        before = catalog_files(snapshot)
        render(snapshot)
        after = catalog_files(snapshot)
        changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
        if not changed:
            return 0
        # Check every destination before writing anything. Partial staging and
        # hand edits must never get silently overwritten by generated output.
        for name in changed:
            path = root / name
            current = path.read_bytes() if path.is_file() else None
            if path.is_symlink() or current not in (before.get(name), after.get(name)):
                print(f"Catalog refresh would overwrite unstaged changes in {name}.")
                print("Stage or save those report edits, then retry the commit.")
                return 1
        for name in changed:
            path = root / name
            if name in after:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(after[name])
            else:
                path.unlink(missing_ok=True)
        print("Catalog refreshed from staged sources. Review these files, stage them, and retry the commit:")
        for name in changed:
            print(f"  {name}")
        print("git add -- " + " ".join(shlex.quote(name) for name in changed))
        return 1


def main() -> int:
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    try:
        return refresh_staged_catalog(root)
    except (subprocess.CalledProcessError, ValueError, OSError) as error:
        print(f"Catalog refresh failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
