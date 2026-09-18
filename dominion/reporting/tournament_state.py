"""Keep tournament evidence inside its report, independently of catalog refreshes."""

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re


SNAPSHOT_ID = "saved-tournament-results"


def tournament_fingerprint(root: Path = Path(".")) -> str:
    """Hash simulation inputs; presentation and guide edits do not affect results."""
    paths = {
        path for path in (root / "dominion").rglob("*.py")
        if "reporting" not in path.relative_to(root / "dominion").parts
    }
    paths.update((root / "generated_strategies").glob("*.py"))
    paths.update(path for path in (root / "boards").rglob("*") if path.is_file())
    paths.update(root / name for name in (
        "compare_all_strategies.py", "requirements.txt", "pyproject.toml",
    ) if (root / name).is_file())
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def make_snapshot(results: dict, context_label: str, fingerprint: str | None) -> dict:
    return {"version": 1, "results": results, "context_label": context_label,
            "input_fingerprint": fingerprint}


def snapshot_markup(snapshot: dict | None) -> str:
    if snapshot is None:
        return ""
    # A strategy name or description must not be able to close the script tag.
    payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=True).replace("<", "\\u003c")
    return f'<script type="application/json" id="{SNAPSHOT_ID}">{payload}</script>'


def tournament_notice(snapshot: dict | None, fingerprint: str) -> str:
    if not snapshot or not snapshot["results"]:
        return ""
    if snapshot["input_fingerprint"] is None:
        return ("These saved tournament results predate input tracking and may be outdated. "
                "Run a new tournament to verify the standings and card ranks.")
    if snapshot["input_fingerprint"] != fingerprint:
        return ("Tournament results are outdated: simulation inputs have changed. "
                "Saved standings and card ranks are retained until you run a new tournament.")
    return ""


class _LegacyStandings(HTMLParser):
    """Recover published evidence from reports created before snapshots existed."""

    def __init__(self):
        super().__init__()
        self.results = {}
        self.cells = None
        self.cell = None
        self.cards = []
        self.context = "a previously saved tournament"
        self.in_context = False
        self.in_description = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "p" and attrs.get("class") == "hero-description":
            self.in_description = True
        if tag == "strong" and self.in_description:
            self.in_context = True
            self.context = ""
        if tag == "tr" and "leaderboard-row" in attrs.get("class", "").split():
            self.cells = []
            self.cards = list(filter(None, attrs.get("data-cards", "").split("|")))
        if tag == "td" and self.cells is not None:
            self.cell = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data
        if self.in_context:
            self.context += data

    def handle_endtag(self, tag):
        if tag == "strong":
            self.in_context = False
        if tag == "p":
            self.in_description = False
        if tag == "td" and self.cells is not None:
            self.cells.append(self.cell.strip())
            self.cell = None
        if tag == "tr" and self.cells is not None:
            if len(self.cells) != 7:
                raise ValueError("Cannot recover saved leaderboard rows; original report was preserved.")
            _, name, description, record, _, games, _ = self.cells
            wins, losses = map(int, record.split("-"))
            games = int(games)
            self.results[name] = {
                "wins": wins, "losses": losses, "games": games,
                "win_rate": wins / games * 100 if games else 0,
                "description": "" if description == "No description" else description,
                "cards": self.cards,
            }
            self.cells = None


def read_snapshot(leaderboard: Path) -> dict | None:
    if not leaderboard.exists():
        return None
    html = leaderboard.read_text(encoding="utf-8")
    match = re.search(
        rf'<script type="application/json" id="{SNAPSHOT_ID}">(.*?)</script>', html, re.DOTALL,
    )
    if match:
        snapshot = json.loads(match[1])
        if (snapshot.get("version") != 1 or not isinstance(snapshot.get("results"), dict)
                or not isinstance(snapshot.get("context_label"), str)
                or "input_fingerprint" not in snapshot):
            raise ValueError("Unsupported saved tournament data; original report was preserved.")
        return snapshot
    legacy = _LegacyStandings()
    legacy.feed(html)
    if legacy.results:
        return make_snapshot(legacy.results, legacy.context, None)
    if "No tournament results yet" in html:
        return None
    raise ValueError("Unrecognized leaderboard; refusing to overwrite saved results.")
