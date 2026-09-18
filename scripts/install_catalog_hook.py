"""Install the catalog pre-commit hook without replacing existing hooks."""

from pathlib import Path
import shlex
import subprocess
import sys


MARKER = "# Dominion catalog refresh hook"


def main() -> int:
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    # Respect core.hooksPath, including hooks shared by linked worktrees. The
    # dispatcher skips branches that do not yet have the catalog hook script.
    hooks = Path(subprocess.check_output(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks"], text=True,
    ).strip())
    destination = hooks / "pre-commit"
    if destination.exists() and MARKER not in destination.read_text():
        print(f"Existing hook preserved: {destination}")
        print(f"Add this command to it: {shlex.quote(sys.executable)} scripts/catalog_pre_commit.py")
        return 1
    hooks.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "#!/bin/sh\n" + MARKER + "\n"
        'catalog_root=$(git rev-parse --show-toplevel) || exit 1\n'
        'cd "$catalog_root" || exit 1\n'
        'if [ -f scripts/catalog_pre_commit.py ]; then\n'
        f"    exec {shlex.quote(sys.executable)} scripts/catalog_pre_commit.py\n"
        "fi\n",
        encoding="utf-8",
    )
    destination.chmod(0o755)
    print(f"Installed {destination} for {root} using {sys.executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
