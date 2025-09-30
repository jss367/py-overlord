#!/usr/bin/env python3
"""Verify that pytest collects every test function in the repository.

The script asks pytest to list the collected tests and cross-checks the
results against the test functions defined under the ``tests`` directory.
It fails with a clear message if any test function is missing from the
collection so the CI logs explicitly show gaps in discovery.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Set, Tuple


CollectedTests = Dict[str, Set[str]]


def run_pytest_collection() -> Tuple[CollectedTests, int | None, str]:
    """Return the tests collected by pytest and its raw output."""

    command = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    process = subprocess.run(command, capture_output=True, text=True)

    if process.returncode != 0:
        # Show pytest's output so the failure is visible in CI logs.
        sys.stdout.write(process.stdout)
        sys.stderr.write(process.stderr)
        sys.exit(process.returncode)

    collected: CollectedTests = defaultdict(set)

    for line in process.stdout.splitlines():
        if "::" not in line:
            continue

        path, _, remainder = line.partition("::")
        test_name = remainder.split("[", 1)[0]
        collected[path].add(test_name)

    reported_total = None
    match = re.search(r"(\d+) tests collected", process.stdout)
    if match:
        reported_total = int(match.group(1))

    return collected, reported_total, process.stdout


def discover_declared_tests(test_root: Path) -> CollectedTests:
    """Find test functions defined in ``test_root`` using the AST."""

    discovered: CollectedTests = defaultdict(set)

    for file_path in test_root.rglob("*.py"):
        if file_path.name == "__init__.py":
            continue

        module = ast.parse(file_path.read_text(), filename=str(file_path))

        for node in module.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                discovered[file_path.as_posix()].add(node.name)

    return discovered


def format_summary(title: str, data: Iterable[Tuple[str, Set[str]]]) -> str:
    lines = [title]
    for path, names in sorted(data):
        lines.append(f"  {path}: {len(names)} test(s)")
    return "\n".join(lines)


def main() -> None:
    collected, reported_total, raw_output = run_pytest_collection()
    declared = discover_declared_tests(Path("tests"))

    missing: Dict[str, Set[str]] = {}

    for path, declared_names in declared.items():
        collected_names = collected.get(path, set())
        missing_names = declared_names - collected_names
        if missing_names:
            missing[path] = missing_names

    print(format_summary("Collected tests per file:", collected.items()))

    if reported_total is not None:
        total_collected = sum(len(names) for names in collected.values())
        print(f"Total collected tests reported by pytest: {reported_total}")
        print(f"Unique test functions collected: {total_collected}")

    if missing:
        print("\nERROR: The following test functions were not collected by pytest:")
        for path, names in sorted(missing.items()):
            for name in sorted(names):
                print(f"  {path}::{name}")
        print("\nFull pytest collection output for reference:\n")
        print(raw_output)
        sys.exit(1)

    print("\nAll test functions in the tests/ directory were collected by pytest.")


if __name__ == "__main__":
    main()
