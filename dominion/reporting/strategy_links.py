"""Shared links for generated board and strategy pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class PageLink:
    """A label and relative URL for another generated catalog page."""

    label: str
    href: str


def strategy_slug(name: str) -> str:
    """Return a stable filename slug for a strategy display name."""

    slug = name.replace("-", " ").replace("_", " ").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug or "strategy"


def strategy_page_href(name: str, *, prefix: str = "strategies") -> str:
    """Return the conventional relative href for a strategy page."""

    return f"{prefix}/{strategy_slug(name)}.html"


def board_display_name(path: Path) -> str:
    """Return an audience-facing name for a board definition path."""

    words = path.stem.replace("-", "_").split("_")
    labels = ["Big Money" if word.lower() == "bm" else word.title() for word in words]
    return " ".join(labels)


def board_page_path(path: Path, *, boards_root: Path = Path("boards")) -> Path:
    """Return the board page path relative to the generated board directory."""

    try:
        relative = path.relative_to(boards_root)
    except ValueError:
        relative = Path(path.name)

    filename = strategy_slug(board_display_name(relative)) + ".html"
    return relative.parent / filename
