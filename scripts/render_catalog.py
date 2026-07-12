"""Render linked Dominion board and strategy catalogs as static HTML."""

from __future__ import annotations

import argparse
from pathlib import Path

from dominion.reporting.catalog_pages import render_catalog_pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Render linked board and strategy HTML pages")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Parent directory for generated boards/ and strategies/ pages (default: reports)",
    )
    args = parser.parse_args()

    written = render_catalog_pages(args.output_dir)
    print(f"Wrote {len(written)} files to {args.output_dir}")
    print(f"Board index: {args.output_dir / 'boards' / 'index.html'}")
    print(f"Strategy index: {args.output_dir / 'strategies' / 'index.html'}")


if __name__ == "__main__":
    main()
