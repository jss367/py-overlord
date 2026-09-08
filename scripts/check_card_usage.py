"""Check generated card usage freshness while allowing tournament rank data."""

import argparse
from difflib import unified_diff
from pathlib import Path

from dominion.reporting.card_usage import normalize_card_usage_for_comparison


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("committed", type=Path)
    parser.add_argument("generated", type=Path)
    args = parser.parse_args()
    committed = normalize_card_usage_for_comparison(args.committed.read_text(encoding="utf-8"))
    generated = normalize_card_usage_for_comparison(args.generated.read_text(encoding="utf-8"))
    if committed == generated:
        return 0
    print("Card strategy usage is stale; regenerate the catalog or tournament report.")
    print("".join(unified_diff(
        committed.splitlines(keepends=True), generated.splitlines(keepends=True),
        fromfile=str(args.committed), tofile=str(args.generated),
    )))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
