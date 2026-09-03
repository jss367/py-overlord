"""Validate the committed, tournament-populated strategy leaderboard."""

from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from dominion.reporting.strategy_links import strategy_slug
from dominion.strategy.strategy_loader import StrategyLoader


class _LeaderboardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_body = False
        self.current_row: list[dict[str, list[str]]] | None = None
        self.current_cell: dict[str, list[str]] | None = None
        self.rows: list[list[dict[str, list[str]]]] = []
        self.hrefs: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "table" and "leaderboard-table" in classes:
            self.in_table = True
        elif tag == "tbody" and self.in_table:
            self.in_body = True
        elif tag == "tr" and self.in_body:
            self.current_row = []
        elif tag == "td" and self.current_row is not None:
            self.current_cell = {"text": [], "hrefs": []}
        elif tag == "a" and (href := attributes.get("href")):
            self.hrefs.append(href)
            if self.current_cell is not None:
                self.current_cell["hrefs"].append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self.current_cell is not None:
            if self.current_row is not None:
                self.current_row.append(self.current_cell)
            self.current_cell = None
        elif tag == "tr" and self.current_row is not None:
            self.rows.append(self.current_row)
            self.current_row = None
        elif tag == "tbody" and self.in_body:
            self.in_body = False
        elif tag == "table" and self.in_table:
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.current_cell is not None:
            self.current_cell["text"].append(data)


def _cell_text(cell: dict[str, list[str]]) -> str:
    return " ".join("".join(cell["text"]).split())


def validate_leaderboard(path: Path) -> list[str]:
    if not path.is_file():
        return [f"leaderboard does not exist: {path}"]

    html = path.read_text(encoding="utf-8")
    parser = _LeaderboardParser()
    parser.feed(html)
    errors: list[str] = []

    if "No tournament results yet" in html:
        errors.append("leaderboard still contains the empty tournament placeholder")
    if 'class="podium"' not in html:
        errors.append("leaderboard is missing the tournament podium")

    expected_names = set(StrategyLoader().list_strategies())
    valid_rows = [row for row in parser.rows if len(row) == 7]
    if len(valid_rows) != len(parser.rows):
        errors.append("every leaderboard row must contain exactly seven columns")

    row_names = [_cell_text(row[1]) for row in valid_rows]
    counts = Counter(row_names)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    missing = sorted(expected_names - set(row_names))
    extra = sorted(set(row_names) - expected_names)
    if duplicates:
        errors.append(f"duplicate strategies: {', '.join(duplicates)}")
    if missing:
        errors.append(f"missing registered strategies: {', '.join(missing)}")
    if extra:
        errors.append(f"unregistered strategies: {', '.join(extra)}")

    for rank, row in enumerate(valid_rows, 1):
        name = _cell_text(row[1])
        if _cell_text(row[0]) != str(rank):
            errors.append(f"{name}: expected rank {rank}")

        expected_href = f"./{strategy_slug(name)}.html"
        if row[1]["hrefs"] != [expected_href]:
            errors.append(f"{name}: expected strategy link {expected_href}")

        record = _cell_text(row[3])
        try:
            wins_text, losses_text = record.split("-", 1)
            wins, losses = int(wins_text), int(losses_text)
            games = int(_cell_text(row[5]))
            win_rate = float(_cell_text(row[4]).removesuffix("%"))
        except ValueError:
            errors.append(f"{name}: invalid record, game count, or win rate")
            continue
        if wins + losses != games:
            errors.append(f"{name}: record {record} does not total {games} games")
        if round(wins / games * 100, 1) != win_rate:
            errors.append(f"{name}: win rate does not match its record")

    for href in parser.hrefs:
        parsed = urlparse(href)
        if parsed.scheme or parsed.netloc:
            continue
        if not (path.parent / parsed.path).resolve().is_file():
            errors.append(f"broken local link: {href}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Leaderboard HTML file to validate")
    args = parser.parse_args()

    errors = validate_leaderboard(args.path)
    if errors:
        raise SystemExit("Invalid strategy leaderboard:\n- " + "\n- ".join(errors))
    print(f"Validated populated strategy leaderboard: {args.path}")


if __name__ == "__main__":
    main()
