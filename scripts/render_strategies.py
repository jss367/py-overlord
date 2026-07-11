"""Render registered Dominion strategies as static HTML pages.

Usage:
    PYTHONPATH=. python scripts/render_strategies.py
    PYTHONPATH=. python scripts/render_strategies.py --strategy "Big Money"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dominion.reporting.strategy_pages import render_strategy_pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Render registered strategies as HTML")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/strategies"),
        help="Directory for generated HTML pages (default: reports/strategies)",
    )
    parser.add_argument(
        "--strategy",
        action="append",
        dest="strategies",
        help="Strategy display name to render. May be passed multiple times. Defaults to all strategies.",
    )
    args = parser.parse_args()

    written = render_strategy_pages(args.output_dir, names=args.strategies)
    print(f"Wrote {len(written)} files to {args.output_dir}")
    print(f"Index: {args.output_dir / 'index.html'}")


if __name__ == "__main__":
    main()
